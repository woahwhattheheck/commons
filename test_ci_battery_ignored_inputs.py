#!/usr/bin/env python3
"""Reject ignored runtime inputs without regressing clean battery execution."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "host" / "ci_battery.py"
REPORTER = ROOT / "host" / "battery_report.py"


class IgnoredInputBatteryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        (self.repo / "host").mkdir()
        shutil.copy2(RUNNER, self.repo / "host" / "ci_battery.py")
        shutil.copy2(REPORTER, self.repo / "host" / "battery_report.py")
        self.test_file = self.repo / "test_a.py"
        self.test_file.write_text("pass\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text(
            "__pycache__/\n*.pyc\nhelper.py\n",
            encoding="utf-8",
        )
        self.output = Path(self.temp.name) / "output"
        self.git("init", "-q")
        self.git("config", "user.name", "CI Test")
        self.git("config", "user.email", "ci-test@example.invalid")
        self.commit("fixture")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, message: str) -> None:
        self.git("add", ".")
        self.git("commit", "-qm", message)
        self.sha = self.git("rev-parse", "HEAD")

    def run_ci(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(self.repo / "host" / "ci_battery.py"),
                "--root",
                str(self.repo),
                "--output-dir",
                str(self.output),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def report(self) -> dict:
        return json.loads((self.output / "report.json").read_text(encoding="utf-8"))

    def test_clean_self_host_does_not_create_ignored_bytecode(self) -> None:
        result = self.run_ci()

        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.report()
        self.assertEqual(report["conclusion"], "PASSED")
        self.assertEqual(report["checkout_sha"], self.sha)
        self.assertEqual(report["execution"]["ignored_worktree_entries_at_start"], 0)
        self.assertIsNone(report["execution"]["preflight_error"])
        self.assertEqual(self.git("status", "--porcelain", "--ignored"), "")
        self.assertFalse(any(self.repo.rglob("__pycache__")))
        self.assertFalse(any(self.repo.rglob("*.pyc")))

    def test_ignored_import_dependency_never_executes(self) -> None:
        marker = Path(self.temp.name) / "ignored-helper-executed.txt"
        self.test_file.write_text(
            "import helper\n"
            "from pathlib import Path\n"
            "assert helper.VALUE == 41\n"
            f"Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n",
            encoding="utf-8",
        )
        self.commit("tracked test imports ignored helper")
        (self.repo / "helper.py").write_text("VALUE = 41\n", encoding="utf-8")
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=all"), "")

        result = self.run_ci()

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("ignored working-tree inputs", result.stderr)
        self.assertFalse(marker.exists(), "tracked test imported ignored working-tree code")
        report = self.report()
        self.assertEqual(report["conclusion"], "HARNESS_FAILED")
        self.assertEqual(report["checkout_sha"], self.sha)
        self.assertEqual(report["counts"]["completed_files"], 0)
        self.assertFalse(report["execution"]["worktree_dirty_at_start"])
        self.assertEqual(report["execution"]["ignored_worktree_entries_at_start"], 1)
        self.assertEqual(report["execution"]["preflight_error"], "ignored_worktree_inputs")
        self.assertEqual(report["execution"]["test_file_sha256"], {})

    def test_external_result_hardlink_cannot_truncate_tracked_test(self) -> None:
        self.output.mkdir()
        try:
            os.link(self.test_file, self.output / "results.nul")
        except OSError as exc:
            self.skipTest(f"hard links unavailable: {exc}")

        result = self.run_ci()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.test_file.read_text(encoding="utf-8"), "pass\n")
        self.assertEqual(self.git("status", "--porcelain"), "")
        report = self.report()
        self.assertEqual(report["conclusion"], "PASSED")
        self.assertEqual(report["counts"]["completed_files"], 1)
        self.assertEqual(report["execution"]["ignored_worktree_entries_at_start"], 0)


if __name__ == "__main__":
    unittest.main()
