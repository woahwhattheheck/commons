#!/usr/bin/env python3
"""Focused hostile tests for deterministic battery-failure census."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / "host/battery_failure_census.py"
SPEC = importlib.util.spec_from_file_location("battery_failure_census", MODULE_PATH)
assert SPEC and SPEC.loader
census = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(census)


class BatteryFailureCensusTests(unittest.TestCase):
    def report_bytes(self, rows):
        return (json.dumps({
            "schema": "commons-battery-report-v1",
            "results": [{"path": path, "exit_code": code} for path, code in rows],
        }, sort_keys=True) + "\n").encode()

    def legacy_bytes(self, rows):
        return (json.dumps({
            "category": "battery",
            "planned_files": [path for path, _ in rows],
            "records": [{"path": path, "duration_seconds": 1.25, "exit_code": code}
                        for path, code in rows],
        }, sort_keys=True) + "\n").encode()

    def parsed_report(self, raw, name="report.json"):
        payload = json.loads(raw)
        return {
            "report_sha256": hashlib.sha256(raw).hexdigest(),
            "source_name": name,
            "rows": census._report_rows(payload),
        }

    def diagnostic(self, report, path, text):
        return {(report["report_sha256"], path): text}

    def test_missing_diagnostic_fails_closed_without_filename_guess(self):
        report = self.parsed_report(self.report_bytes([
            ("test_paper_reference_manifest.py", 1), ("test_ok.py", 0)
        ]))
        result = census.build_census([report], {})
        self.assertEqual(result["summary"]["incomplete_evidence"], 1)
        self.assertEqual(result["summary"]["remint"], 0)
        self.assertEqual(result["remint_queue"], [])
        self.assertFalse(result["failures"][0]["diagnostic_bound"])

    def test_strong_stale_pin_mismatch_enters_remint_queue(self):
        report = self.parsed_report(self.report_bytes([("test_manifest.py", 1)]))
        diagnostics = self.diagnostic(
            report, "test_manifest.py",
            "AssertionError: pinned manifest SHA abcdef012345 differs; "
            "expected abcdef012345, actual 1234567890ab",
        )
        result = census.build_census([report], diagnostics)
        self.assertEqual(result["summary"]["remint"], 1)
        self.assertEqual(result["remint_queue"][0]["path"], "test_manifest.py")
        self.assertNotIn("pinned manifest", json.dumps(result))
        self.assertRegex(result["failures"][0]["diagnostic_sha256"], r"^[0-9a-f]{64}$")

    def test_manifest_filename_with_ordinary_assertion_stays_semantic(self):
        report = self.parsed_report(self.report_bytes([("test_manifest.py", 1)]))
        result = census.build_census(
            [report], self.diagnostic(report, "test_manifest.py", "AssertionError: 2 != 3"))
        self.assertEqual(result["failures"][0]["category"], "semantic_assertion")
        self.assertEqual(result["remint_queue"], [])

    def test_harness_timeout_is_not_semantic(self):
        report = self.parsed_report(self.report_bytes([("test_x.py", 124)]))
        result = census.build_census(
            [report], self.diagnostic(report, "test_x.py", "test timed out: test_x.py"))
        self.assertEqual(result["failures"][0]["category"], "harness_failure")

    def test_unknown_diagnostic_remains_incomplete(self):
        report = self.parsed_report(self.report_bytes([("test_x.py", 9)]))
        result = census.build_census(
            [report], self.diagnostic(report, "test_x.py", "exited nonzero without details"))
        self.assertEqual(result["failures"][0]["category"], "incomplete_evidence")

    def test_repeated_remint_failures_are_aggregated_by_path(self):
        first = self.parsed_report(self.report_bytes([("test_x.py", 1)]), "first.json")
        second = self.parsed_report(self.legacy_bytes([("test_x.py", 1), ("test_y.py", 0)]),
                                    "second.json")
        diagnostics = {}
        diagnostics.update(self.diagnostic(
            first, "test_x.py", "stale manifest hash detected"))
        diagnostics.update(self.diagnostic(
            second, "test_x.py", "manifest pinned SHA mismatch: expected aaaaaaa, got bbbbbbb"))
        result = census.build_census([second, first], diagnostics)
        self.assertEqual(result["remint_queue"][0]["occurrences"], 2)
        self.assertEqual(result["remint_queue"][0]["report_sha256"],
                         sorted([first["report_sha256"], second["report_sha256"]]))

    def test_diagnostic_must_bind_to_exact_report_and_existing_path(self):
        report = self.parsed_report(self.report_bytes([("test_x.py", 1)]))
        with self.assertRaisesRegex(census.CensusError, "report not in this census"):
            census.build_census([report], {("0" * 64, "test_x.py"): "AssertionError"})
        with self.assertRaisesRegex(census.CensusError, "absent from failed records"):
            census.build_census(
                [report], {(report["report_sha256"], "test_other.py"): "AssertionError"})

        mixed = self.parsed_report(self.report_bytes([("test_ok.py", 0), ("test_x.py", 1)]))
        with self.assertRaisesRegex(census.CensusError, "absent from failed records"):
            census.build_census(
                [mixed], {(mixed["report_sha256"], "test_ok.py"): "AssertionError"})

    def test_duplicate_report_paths_and_bytes_are_rejected(self):
        with self.assertRaisesRegex(census.CensusError, "duplicate test path"):
            census._report_rows({
                "schema": "commons-battery-report-v1",
                "results": [
                    {"path": "test_x.py", "exit_code": 1},
                    {"path": "test_x.py", "exit_code": 2},
                ],
            })
        with tempfile.TemporaryDirectory() as temp:
            a = Path(temp) / "a.json"
            b = Path(temp) / "b.json"
            raw = self.report_bytes([("test_x.py", 1)])
            a.write_bytes(raw)
            b.write_bytes(raw)
            with self.assertRaisesRegex(census.CensusError, "duplicate report bytes"):
                census.load_reports([a, b])

    def test_invalid_report_schema_path_and_exit_are_rejected(self):
        cases = [
            {"schema": "future-v9", "results": []},
            {"schema": "commons-battery-report-v1",
             "results": [{"path": "../escape.py", "exit_code": 1}]},
            {"schema": "commons-battery-report-v1",
             "results": [{"path": "test_x.py", "exit_code": True}]},
            {"records": []},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(census.CensusError):
                    census._report_rows(payload)

    def test_cli_is_deterministic_and_report_only_failure_stays_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            report = temp / "report.json"
            out1 = temp / "one.json"
            out2 = temp / "two.json"
            report.write_bytes(self.legacy_bytes([
                ("test_paper_reference_manifest.py", 1),
                ("test_sidebar_analysis_contract.py", 1),
                ("test_source_contracts.py", 1),
                ("test_ok.py", 0),
            ]))
            for output in (out1, out2):
                run = subprocess.run(
                    [sys.executable, str(MODULE_PATH), str(report), "--output", str(output)],
                    cwd=ROOT, capture_output=True, text=True,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())
            result = json.loads(out1.read_text())
            self.assertEqual(result["summary"]["failed_file_records"], 3)
            self.assertEqual(result["summary"]["incomplete_evidence"], 3)
            self.assertEqual(result["remint_queue"], [])


if __name__ == "__main__":
    unittest.main()
