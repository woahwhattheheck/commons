#!/usr/bin/env python3
"""Regression for battery-report harness-failure precedence with unbound source."""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from host import battery_report as report


def stream(*records):
    return b"".join(
        str(field).encode("utf-8") + b"\0"
        for record in records
        for field in record
    )


class BatteryHarnessFailedPrecedenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Battery Precedence Test")
        self.git("config", "user.email", "battery-precedence@example.invalid")
        (self.root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("commit", "-qm", "fixture")
        self.sha = self.git("rev-parse", "HEAD")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def raw_untracked_zero_exit(self):
        return stream(
            ("checkout_sha", self.sha, ""),
            ("node", "test_not_tracked.js", 0),
            ("battery_complete", "", 0),
        )

    def test_harness_failure_keeps_stronger_conclusion_with_unbound_source(self):
        data = report.build_report(self.root, self.raw_untracked_zero_exit(), "failure", {})
        self.assertTrue(data["complete"])
        self.assertEqual(data["conclusion"], "HARNESS_FAILED")
        self.assertEqual(data["counts"]["failed_files"], 0)
        self.assertEqual(data["counts"]["unresolved_source_files"], 1)
        self.assertFalse(data["results"][0]["source_in_checkout_commit"])

    def test_success_with_same_unbound_source_remains_incomplete(self):
        data = report.build_report(self.root, self.raw_untracked_zero_exit(), "success", {})
        self.assertFalse(data["complete"])
        self.assertEqual(data["conclusion"], "INCOMPLETE")
        self.assertEqual(data["counts"]["unresolved_source_files"], 1)
        self.assertIn(
            "passing executed file(s) are not present in the recorded checkout",
            " ".join(data["problems"]),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
