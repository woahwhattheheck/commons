#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-contained report-parser fixtures, not gameplay or execution evidence."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import build_combined_report as subject


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def log(n, status="OK", trailer=""):
    return f"test_fixture ... ok\n\n----------------------------------------------------------------------\nRan {n} tests in 0.100s\n\n{status}\n{trailer}"


def fixture(directory):
    paths = {row[2] for row in subject.SUITES}
    paths.update(subject.LAB + p for p in (
        "selected_action_sell.py", "selected_sell_core.py", "mechanics.py",
        "reference/decision/decision.py", "ordered_selected_sell.py",
        "reference/evaluator/evaluate.py", "reference/evaluator/loader.py",
        "reference/engine/kaggriculture.py", "reference/engine/kaggriculture.json",
        "reference/engine/utils.py"))
    paths.add(subject.PROJECTION + "projection.py")
    snapshot = dict(checkout="a" * 40, run_id="123", attempt="1", python="fixture",
                    files={p: {"sha256": sha(p)} for p in paths})
    save(directory / "SOURCE-SNAPSHOT.json", snapshot)
    counts = dict(original=16, projection=21, market=14, loader=7, empty_lot=15, joined_wrapper=6)
    for key, name, _, _, _ in subject.SUITES:
        (directory / name).write_text(log(counts[key]), encoding="utf-8")
    engine = {p: sha(subject.LAB + "reference/engine/" + p)
              for p in ("kaggriculture.py", "kaggriculture.json", "utils.py")}
    save(directory / "projection-results.json", dict(tests_run=21, failures=0, errors=0,
        differential_cases=144, interpreter_transitions=378, engine_sha256=engine,
        seller_sha256=sha(subject.LAB + "selected_action_sell.py"),
        projection_sha256=sha(subject.PROJECTION + "projection.py")))
    save(directory / "market-results.json", dict(test_methods=14, failures=0, errors=0,
        successful=True, official_market_cases=28, engine_sha256=engine,
        sources={p: sha(subject.LAB + p) for p in (
            "selected_action_sell.py", "selected_sell_core.py", "mechanics.py", "reference/decision/decision.py")}))
    save(directory / "loader-results.json", dict(test_methods=7, failures=0, errors=0,
        successful=True, official_market_cases=4, source_sha256=dict(
            checker=sha(subject.MARKET + "check_market_contracts.py"),
            evaluator=sha(subject.LAB + "reference/evaluator/evaluate.py"),
            loader=sha(subject.LAB + "reference/evaluator/loader.py"))))


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        fixture(self.path)

    def report(self, **kwargs):
        return subject.build_report(self.path, **kwargs)

    def mutate(self, name, change):
        path = self.path / name
        value = json.loads(path.read_text())
        change(value)
        save(path, value)

    def test_six_suites_total_79_instead_of_legacy_51(self):
        report = self.report()
        self.assertTrue(report["successful"], report["problems"])
        self.assertTrue(report["complete"])
        self.assertEqual(report["total_tests"], 79)
        self.assertEqual(report["legacy_three_suite_tests"], 51)
        self.assertEqual(report["suite_count"], 6)
        self.assertEqual(report["full_games"], 0)

    def test_reporter_suite_is_explicit_and_counted_when_requested(self):
        self.mutate("SOURCE-SNAPSHOT.json", lambda d: d["files"].update({subject.REPORTER[2]: {"sha256": sha("reporter")}}))
        (self.path / "reporter-tests.log").write_text(log(20))
        report = self.report(include_reporter=True)
        self.assertTrue(report["successful"], report["problems"])
        self.assertEqual(report["total_tests"], 99)
        self.assertEqual(report["reporter_tests"], 20)
        self.assertEqual(self.report()["total_tests"], 79)

    def test_missing_extended_suites_preserve_known_51_not_complete(self):
        for name in ("loader-tests.log", "empty-lot-tests.log", "joined-wrapper-tests.log", "loader-results.json"):
            (self.path / name).unlink()
        report = self.report()
        self.assertFalse(report["successful"])
        self.assertFalse(report["complete"])
        self.assertEqual(report["observed_tests"], 51)
        self.assertIsNone(report["total_tests"])
        self.assertIsNone(report["loader_tests"])

    def test_missing_reporter_does_not_silently_pass(self):
        report = self.report(include_reporter=True)
        self.assertFalse(report["successful"])
        self.assertIsNone(report["reporter_tests"])

    def test_failed_suite_is_not_counted_as_pass(self):
        (self.path / "empty-lot-tests.log").write_text(log(15, "FAILED (failures=1)"))
        report = self.report()
        self.assertFalse(report["successful"])
        self.assertEqual(report["total_tests"], 79)
        self.assertEqual(report["suites"]["empty_lot"]["failures"], 1)

    def test_skipped_or_expected_failure_is_not_a_full_pass(self):
        for status in ("OK (skipped=1)", "OK (expected failures=1)"):
            with self.subTest(status=status):
                (self.path / "original-seller-tests.log").write_text(log(16, status))
                self.assertFalse(self.report()["successful"])

    def test_zero_methods_do_not_pass(self):
        (self.path / "empty-lot-tests.log").write_text(log(0))
        self.assertFalse(self.report()["successful"])

    def test_truncated_and_duplicate_run_summaries_do_not_pass(self):
        for text in (log(15).replace("\nOK\n", "\n"), log(15) + log(15), log(15) + "\nRan 2 tests in 0.1s\n"):
            with self.subTest(text=text[-60:]):
                (self.path / "empty-lot-tests.log").write_text(text)
                report = self.report()
                self.assertFalse(report["successful"])
                self.assertIsNone(report["empty_lot_tests"])

    def test_trailing_report_accepted_but_traceback_not_accepted(self):
        self.assertTrue(subject.parse_unittest(log(2, trailer='{"test_methods":2}\n'))["successful"])
        with self.assertRaises(ValueError):
            subject.parse_unittest(log(2, trailer="Traceback (most recent call last):\nRuntimeError: stopped\n"))

    def test_json_log_count_mismatch(self):
        self.mutate("market-results.json", lambda d: d.update(test_methods=13))
        self.assertFalse(self.report()["successful"])

    def test_failed_json_cannot_be_hidden_by_ok_log(self):
        self.mutate("projection-results.json", lambda d: d.update(errors=1))
        self.assertFalse(self.report()["successful"])

    def test_seller_drift_and_projection_drift(self):
        for field in ("seller_sha256", "projection_sha256"):
            with self.subTest(field=field):
                fixture(self.path)
                self.mutate("projection-results.json", lambda d: d.update({field: "0" * 64}))
                self.assertFalse(self.report()["successful"])

    def test_engine_json_agreement_alone_does_not_replace_snapshot_binding(self):
        for name in ("projection-results.json", "market-results.json"):
            self.mutate(name, lambda d: d["engine_sha256"].update({"utils.py": "0" * 64}))
        report = self.report()
        self.assertFalse(report["same_engine"])
        self.assertFalse(report["successful"])

    def test_loader_hash_is_bound_to_recorded_source(self):
        self.mutate("loader-results.json", lambda d: d["source_sha256"].update(loader="0" * 64))
        self.assertFalse(self.report()["successful"])

    def test_missing_suite_source_row_is_explicit(self):
        self.mutate("SOURCE-SNAPSHOT.json", lambda d: d["files"].pop(subject.LAB + "test_ordered_selected_sell.py"))
        report = self.report()
        self.assertFalse(report["successful"])
        self.assertIsNone(report["suites"]["joined_wrapper"]["test_source_sha256"])

    def test_duplicate_json_keys_are_not_silently_overwritten(self):
        (self.path / "loader-results.json").write_text('{"test_methods":0,"test_methods":7}')
        self.assertFalse(self.report()["successful"])

    def test_malformed_snapshot_has_an_explicit_report(self):
        (self.path / "SOURCE-SNAPSHOT.json").write_text('{"files":[')
        report = self.report()
        self.assertFalse(report["successful"])
        self.assertTrue(report["problems"])

    def test_boolean_counts_do_not_equal_integer_evidence(self):
        self.mutate("market-results.json", lambda d: d.update(failures=False))
        self.assertFalse(self.report()["successful"])

    def test_outputs_are_deterministic_and_inputs_unchanged(self):
        before = {p.name: p.read_bytes() for p in self.path.iterdir()}
        first = self.report()
        self.assertEqual(first, self.report())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.path.iterdir()})
        self.assertEqual(first["input_sha256"]["empty-lot-tests.log"], hashlib.sha256(before["empty-lot-tests.log"]).hexdigest())

    def test_cli_exit_and_serialized_partial_report(self):
        output = self.path / "output.json"
        cmd = [sys.executable, str(Path(subject.__file__)), "--directory", str(self.path), "--output", str(output)]
        ok = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(output.read_text())["total_tests"], 79)
        (self.path / "joined-wrapper-tests.log").unlink()
        bad = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1, bad.stderr)
        self.assertIsNone(json.loads(output.read_text())["total_tests"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
