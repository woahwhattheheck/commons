#!/usr/bin/env python3
"""Fail-closed regressions for direct battery provenance."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "host/ci_battery.py"


class DirtyWorktreeBatteryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.out = Path(self.temp.name) / "output"
        self.git("init", "-q")
        self.git("config", "user.name", "CI Test")
        self.git("config", "user.email", "ci-test@example.invalid")
        self.test_file = self.root / "test_a.py"
        self.test_file.write_text("pass\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.sha = self.git("rev-parse", "HEAD")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def run_ci(self):
        return subprocess.run(
            [sys.executable, str(RUNNER), "--root", str(self.root),
             "--output-dir", str(self.out)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def report(self):
        return json.loads((self.out / "report.json").read_text(encoding="utf-8"))

    def assert_dirty_rejected(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("checkout is dirty", result.stderr)
        report = self.report()
        self.assertEqual(report["conclusion"], "HARNESS_FAILED")
        self.assertEqual(report["checkout_sha"], self.sha)
        self.assertTrue(report["execution"]["worktree_dirty_at_start"])
        self.assertEqual(report["counts"]["completed_files"], 0)
        self.assertEqual(report["execution"]["test_file_sha256"], {})

    def test_tracked_modification_never_executes_or_passes(self):
        marker = Path(self.temp.name) / "executed.txt"
        self.test_file.write_text(
            "from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('ran')\n",
            encoding="utf-8",
        )
        result = self.run_ci()
        self.assert_dirty_rejected(result)
        self.assertFalse(marker.exists())

    def test_untracked_file_never_allows_passing_evidence(self):
        (self.root / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")
        self.assert_dirty_rejected(self.run_ci())


if __name__ == "__main__":
    unittest.main()
