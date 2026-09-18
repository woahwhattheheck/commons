#!/usr/bin/env python3
"""Fail-closed regressions for direct battery provenance."""
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
        self.assertEqual(report["execution"]["preflight_error"], "dirty_worktree")
        self.assertEqual(report["counts"]["completed_files"], 0)
        self.assertEqual(report["execution"]["test_file_sha256"], {})

    def assert_unbound_rejected(self, result, tracked_marker=None, injected_marker=None):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("tracked regular files", result.stderr)
        if tracked_marker is not None:
            self.assertFalse(tracked_marker.exists())
        if injected_marker is not None:
            self.assertFalse(injected_marker.exists())
        report = self.report()
        self.assertEqual(report["conclusion"], "HARNESS_FAILED")
        self.assertEqual(report["checkout_sha"], self.sha)
        self.assertEqual(report["counts"]["completed_files"], 0)
        self.assertEqual(report["execution"]["test_file_sha256"], {})
        self.assertEqual(report["execution"]["preflight_error"], "selected_not_tracked_regular")

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

    def test_ignored_selected_test_never_executes_or_passes(self):
        tracked_marker = Path(self.temp.name) / "tracked-ran.txt"
        injected_marker = Path(self.temp.name) / "ignored-ran.txt"
        self.test_file.write_text(
            "from pathlib import Path\nPath(" + repr(str(tracked_marker)) + ").write_text('ran')\n",
            encoding="utf-8",
        )
        (self.root / ".gitignore").write_text("test_injected.py\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "ignore injected tests")
        self.sha = self.git("rev-parse", "HEAD")
        (self.root / "test_injected.py").write_text(
            "from pathlib import Path\nPath(" + repr(str(injected_marker)) + ").write_text('ran')\n",
            encoding="utf-8",
        )
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assert_unbound_rejected(self.run_ci(), tracked_marker, injected_marker)
        self.assertFalse(self.report()["execution"]["worktree_dirty_at_start"])

    @unittest.skipUnless(shutil.which("node"), "requires Node")
    def test_node_symlink_never_executes_or_passes(self):
        marker = Path(self.temp.name) / "node-ran.txt"
        outside = Path(self.temp.name) / "outside.js"
        outside.write_text(
            "require('fs').writeFileSync(" + json.dumps(str(marker)) + ", 'ran');\n",
            encoding="utf-8",
        )
        link = self.root / "test_link.js"
        os.symlink(outside, link)
        self.git("add", "test_link.js")
        self.git("commit", "-qm", "symlink node test")
        self.sha = self.git("rev-parse", "HEAD")
        self.assert_unbound_rejected(self.run_ci(), injected_marker=marker)

    def test_in_checkout_results_do_not_self_dirty_a_clean_tree(self):
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--root", str(self.root),
             "--results", str(self.root / "results.nul"),
             "--report", str(self.out / "report.json")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((self.out / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["conclusion"], "PASSED")
        self.assertFalse(report["execution"]["worktree_dirty_at_start"])
        self.assertIsNone(report["execution"]["preflight_error"])
        self.assertEqual(report["counts"]["completed_files"], 1)


if __name__ == "__main__":
    unittest.main()
