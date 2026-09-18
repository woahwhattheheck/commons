#!/usr/bin/env python3
"""Offline regressions: duplicate exit records are not complete file evidence."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import battery_report as report

SHA = "a" * 40
ROOT = Path(__file__).resolve().parent
DIAGNOSTIC = "duplicate repository-relative test path"


def stream(*records):
    return b"".join(str(field).encode("utf-8") + b"\0"
                    for record in records for field in record)


def raw(*records, sha=SHA, failed=0):
    return stream(("checkout_sha", sha, ""), *records,
                  ("battery_complete", "", failed))


class DuplicateResultParserTests(unittest.TestCase):
    def check_duplicate(self, *rows, failed=0):
        sha, records, complete, problems = report.parse_results(raw(*rows, failed=failed))
        self.assertEqual(sha, SHA)
        self.assertFalse(complete)
        self.assertIn(DIAGNOSTIC, problems)
        # Every exit and original invocation remains inspectable; no first/last-wins.
        self.assertEqual(len(records), len(rows))
        self.assertEqual([r["exit_code"] for r in records], [r[2] for r in rows])
        self.assertEqual([r["command"] for r in records], [[r[0], r[1]] for r in rows])
        return records, problems

    def test_identical_successful_records_are_incomplete(self):
        self.check_duplicate(("python3", "test_a.py", 0), ("python3", "test_a.py", 0))

    def test_dot_prefix_alias_is_the_same_file(self):
        records, _ = self.check_duplicate(("python3", "./test_a.py", 0),
                                          ("python3", "test_a.py", 0))
        self.assertEqual([r["path"] for r in records], ["test_a.py", "test_a.py"])

    def test_normalized_separator_and_dot_aliases_are_detected(self):
        self.check_duplicate(("python3", "infra//./test_a.py", 0),
                             ("python3", "infra/test_a.py", 0))

    def test_different_interpreters_do_not_inflate_file_evidence(self):
        self.check_duplicate(("python3", "test_a.py", 0), ("node", "./test_a.py", 0))

    def test_later_success_does_not_hide_earlier_failure(self):
        self.check_duplicate(("python3", "test_a.py", 7), ("python3", "test_a.py", 0), failed=1)

    def test_later_failure_is_preserved(self):
        self.check_duplicate(("python3", "test_a.py", 0), ("python3", "test_a.py", 9), failed=1)

    def test_each_repeated_record_remains_visible(self):
        _, problems = self.check_duplicate(*[("python3", "test_a.py", 0)] * 3)
        self.assertEqual(problems.count(DIAGNOSTIC), 2)

    def test_unusual_filename_remains_lossless(self):
        path = "test_a | <b>`\n\t.py"
        records, _ = self.check_duplicate(("python3", path, 0), ("python3", "./" + path, 0))
        self.assertEqual(records[0]["path"], path)

    def test_distinct_paths_still_complete(self):
        _, records, complete, problems = report.parse_results(raw(
            ("python3", "test_a.py", 0), ("node", "test_b.js", 0)))
        self.assertTrue(complete)
        self.assertEqual(len(records), 2)
        self.assertEqual(problems, [])

    def test_equal_basenames_in_different_directories_are_distinct(self):
        _, _, complete, problems = report.parse_results(raw(
            ("python3", "test_a.py", 0), ("python3", "infra/test_a.py", 0)))
        self.assertTrue(complete)
        self.assertEqual(problems, [])

    def test_posix_case_distinctions_are_preserved(self):
        _, _, complete, problems = report.parse_results(raw(
            ("python3", "test_a.py", 0), ("python3", "test_A.py", 0)))
        self.assertTrue(complete)
        self.assertEqual(problems, [])

    def test_invalid_path_is_not_silently_accepted_or_counted(self):
        _, records, complete, problems = report.parse_results(raw(
            ("python3", "../test_a.py", 0), ("python3", "test_a.py", 0)))
        self.assertFalse(complete)
        self.assertEqual(len(records), 1)
        self.assertIn("invalid repository-relative test path", problems)
        self.assertNotIn(DIAGNOSTIC, problems)

    def test_completion_disagreement_is_still_retained(self):
        _, _, complete, problems = report.parse_results(raw(
            ("python3", "test_a.py", 7), ("python3", "test_a.py", 0), failed=0))
        self.assertFalse(complete)
        self.assertIn("completion marker disagrees with recorded exits", problems)
        self.assertIn(DIAGNOSTIC, problems)


class DuplicateResultReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        def git(*args):
            return subprocess.run(["git", "-C", str(cls.root), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        git("init", "-q")
        git("config", "user.name", "Battery Duplicate Fixture")
        git("config", "user.email", "fixture@example.invalid")
        (cls.root / "test_a.py").write_text("pass\n", encoding="utf-8")
        git("add", "test_a.py")
        git("commit", "-qm", "fixture")
        cls.sha = git("rev-parse", "HEAD")
        cls.blob = git("rev-parse", "HEAD:test_a.py")

    def test_duplicate_success_is_not_reported_as_passed(self):
        data = report.build_report(self.root, raw(
            ("python3", "test_a.py", 0), ("python3", "./test_a.py", 0), sha=self.sha),
            "success", {"GITHUB_SHA": "b" * 40})
        self.assertEqual(data["conclusion"], "INCOMPLETE")
        self.assertFalse(data["complete"])
        self.assertEqual(data["checkout_sha"], self.sha)
        self.assertEqual(data["event_sha"], "b" * 40)
        self.assertEqual(data["counts"]["completed_files"], 2)
        self.assertEqual([r["source_blob_sha"] for r in data["results"]], [self.blob] * 2)
        self.assertIn(DIAGNOSTIC, report.summary(data))

    def test_failure_evidence_is_kept_under_incomplete_conclusion(self):
        data = report.build_report(self.root, raw(
            ("python3", "test_a.py", 7), ("python3", "./test_a.py", 0),
            sha=self.sha, failed=1), "failure", {})
        self.assertEqual(data["conclusion"], "INCOMPLETE")
        self.assertEqual(data["counts"]["failed_files"], 1)
        self.assertEqual(data["counts"]["passed_files"], 1)
        self.assertIn("| 7 |", report.summary(data))

    def test_unique_control_still_passes(self):
        data = report.build_report(self.root, raw(("python3", "test_a.py", 0), sha=self.sha),
                                   "success", {})
        self.assertEqual(data["conclusion"], "PASSED")
        self.assertTrue(data["complete"])
        self.assertEqual(data["problems"], [])

    def test_cli_keeps_reporting_exit_contract(self):
        results = self.root / "duplicates.nul"
        output = self.root / "duplicates.json"
        results.write_bytes(raw(("python3", "test_a.py", 0),
                                ("python3", "./test_a.py", 0), sha=self.sha))
        process = subprocess.run([
            sys.executable, str(ROOT / "host/battery_report.py"),
            "--root", str(self.root), "--results", str(results),
            "--output", str(output), "--outcome", "success",
        ], capture_output=True, text=True, timeout=15)
        # The workflow's original test command, not this reporter, controls CI.
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["conclusion"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
