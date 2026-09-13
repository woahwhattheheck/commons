#!/usr/bin/env python3
"""Fail-closed clean-checkout contracts for the portable CI battery."""
from __future__ import annotations

import json
import os
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

    def assert_preflight_failure(
        self,
        result: subprocess.CompletedProcess[str],
        output: Path,
        expected_error: str,
    ) -> dict:
        self.assertEqual(result.returncode, 2, result.stderr)
        report = self.report(output)
        self.assertEqual(report["conclusion"], "INCOMPLETE")
        self.assertEqual(report["counts"]["completed_files"], 0)
        self.assertEqual(report["execution"]["preflight_error"], expected_error)
        self.assertEqual(report["execution"]["test_file_sha256"], {})
        return report

    def test_dirty_tracked_test_is_rejected_without_execution(self):
        marker = Path(self.temp.name) / "executed.txt"
        self.test_file.write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n",
            encoding="utf-8",
        )
        output = Path(self.temp.name) / "dirty-output"

        result = self.run_battery(output)

        self.assertFalse(marker.exists(), "dirty working-tree bytes were executed")
        report = self.assert_preflight_failure(result, output, "dirty_worktree")
        self.assertTrue(report["execution"]["worktree_dirty_at_start"])
        self.assertEqual(report["execution"]["source_binding_errors"], [])

    def test_output_inside_checkout_is_rejected_before_creation(self):
        output = self.repo / "ci-output"

        result = self.run_battery(output)

        self.assertEqual(result.returncode, 2)
        self.assertIn("output paths must be outside", result.stderr)
        self.assertFalse(output.exists())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_external_hardlink_result_cannot_truncate_tracked_test(self):
        output = Path(self.temp.name) / "hardlink-output"
        output.mkdir()
        try:
            os.link(self.test_file, output / "results.nul")
        except OSError as exc:
            self.skipTest(f"hard links unavailable: {exc}")

        result = self.run_battery(output)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.test_file.read_text(encoding="utf-8"), "pass\n")
        self.assertEqual(self.git("status", "--porcelain"), "")
        report = self.report(output)
        self.assertEqual(report["conclusion"], "PASSED")
        self.assertEqual(report["counts"]["completed_files"], 1)
        self.assertEqual(report["execution"]["source_binding_errors"], [])

    def test_ignored_discovered_test_is_rejected_without_execution(self):
        (self.repo / ".gitignore").write_text("test_injected.py\n", encoding="utf-8")
        self.commit("ignore injected test")
        marker = Path(self.temp.name) / "ignored-test-executed.txt"
        (self.repo / "test_injected.py").write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n",
            encoding="utf-8",
        )
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=all"), "")
        output = Path(self.temp.name) / "ignored-test-output"

        result = self.run_battery(output)

        self.assertFalse(marker.exists(), "ignored test bytes were executed")
        report = self.assert_preflight_failure(result, output, "dirty_worktree")
        self.assertTrue(report["execution"]["worktree_dirty_at_start"])

    def test_ignored_import_dependency_cannot_authorize_pass(self):
        marker = Path(self.temp.name) / "ignored-helper-executed.txt"
        (self.repo / ".gitignore").write_text("helper.py\n", encoding="utf-8")
        self.test_file.write_text(
            "import helper\n"
            "from pathlib import Path\n"
            "assert helper.VALUE == 41\n"
            f"Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n",
            encoding="utf-8",
        )
        self.commit("tracked test with ignored dependency pattern")
        (self.repo / "helper.py").write_text("VALUE = 41\n", encoding="utf-8")
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=all"), "")
        output = Path(self.temp.name) / "ignored-helper-output"

        result = self.run_battery(output)

        self.assertFalse(marker.exists(), "tracked test imported ignored working-tree code")
        report = self.assert_preflight_failure(result, output, "dirty_worktree")
        self.assertTrue(report["execution"]["worktree_dirty_at_start"])

    def test_tracked_node_symlink_is_rejected_without_execution(self):
        marker = Path(self.temp.name) / "node-symlink-executed.txt"
        target = Path(self.temp.name) / "outside-test.js"
        target.write_text(
            "require('fs').writeFileSync("
            + json.dumps(str(marker))
            + ", 'ran');\n",
            encoding="utf-8",
        )
        link = self.repo / "test_link.js"
        try:
            link.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        self.commit("tracked node symlink")
        if not self.git("ls-files", "-s", "test_link.js").startswith("120000 "):
            self.skipTest("Git did not record the fixture as a symlink")
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=all"), "")
        output = Path(self.temp.name) / "node-symlink-output"

        result = self.run_battery(output)

        self.assertFalse(marker.exists(), "out-of-checkout Node target was executed")
        report = self.assert_preflight_failure(result, output, "unbound_test_sources")
        self.assertFalse(report["execution"]["worktree_dirty_at_start"])
        errors = {
            row["path"]: row["problems"]
            for row in report["execution"]["source_binding_errors"]
        }
        self.assertIn("test_link.js", errors)
        self.assertIn("checkout_mode_120000", errors["test_link.js"])
        self.assertIn("working_tree_path_not_regular", errors["test_link.js"])


if __name__ == "__main__":
    unittest.main()
