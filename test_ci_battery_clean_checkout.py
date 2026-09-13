#!/usr/bin/env python3
"""Fail-closed clean-checkout contracts for the portable CI battery."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "host" / "ci_battery.py"


class CleanCheckoutBatteryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "CI Test")
        self.git("config", "user.email", "ci-test@example.invalid")
        self.test_file = self.repo / "test_ok.py"
        self.test_file.write_text("pass\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def run_battery(self, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--root",
                str(self.repo),
                "--output-dir",
                str(output),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

    @staticmethod
    def report(output: Path) -> dict:
        return json.loads((output / "report.json").read_text(encoding="utf-8"))

    def test_dirty_tracked_test_is_rejected_without_execution(self):
        marker = Path(self.temp.name) / "executed.txt"
        self.test_file.write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n",
            encoding="utf-8",
        )
        output = Path(self.temp.name) / "dirty-output"

        result = self.run_battery(output)

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(marker.exists(), "dirty working-tree bytes were executed")
        report = self.report(output)
        self.assertEqual(report["conclusion"], "INCOMPLETE")
        self.assertEqual(report["counts"]["completed_files"], 0)
        self.assertTrue(report["execution"]["worktree_dirty_at_start"])
        self.assertEqual(report["execution"]["preflight_error"], "dirty_worktree")
        self.assertEqual(report["execution"]["test_file_sha256"], {})

    def test_output_inside_checkout_is_rejected_before_creation(self):
        output = self.repo / "ci-output"

        result = self.run_battery(output)

        self.assertEqual(result.returncode, 2)
        self.assertIn("output paths must be outside", result.stderr)
        self.assertFalse(output.exists())
        self.assertEqual(self.git("status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
