#!/usr/bin/env python3
"""Exercise viewport inventory startup failures with real child processes.

No subprocess call is mocked. POSIX-only executable-layout fixtures are
explicitly skipped on other platforms; ordinary missing-Git, recovery and
real-Git checks remain portable.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().with_name("viewport_check.py")
REAL_GIT = shutil.which("git")
PAGE = b'<!doctype html><meta name="viewport" content="width=device-width">\n'


class ViewportInventoryLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="viewport-launch-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.page = self.repo / "page.html"
        self.page.write_bytes(PAGE)

    def invoke(self, path=None, cwd=None):
        env = os.environ.copy()
        if path is not None:
            env["PATH"] = str(path)
        return subprocess.run(
            [sys.executable, "-B", str(CHECKER)],
            cwd=self.repo if cwd is None else cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

    def assert_start_failure(self, done):
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertEqual(done.stdout, "")
        self.assertIn("viewport census: INVENTORY FAILED:", done.stderr)
        self.assertIn("git ls-files could not start:", done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        self.assertNotIn("NO VIEWPORT", done.stderr)
        self.assertNotIn("documents checked", done.stderr)
        self.assertEqual(len(done.stderr.splitlines()), 1)
        self.assertLess(len(done.stderr), 400)
        self.assertEqual(self.page.read_bytes(), PAGE)

    def init_repo(self):
        if REAL_GIT is None:
            self.skipTest("real Git is required for the success controls")
        for args in (("init", "-q"), ("add", "page.html")):
            done = subprocess.run(
                [REAL_GIT, *args], cwd=self.repo, capture_output=True,
                text=True, check=False, timeout=10,
            )
            self.assertEqual(done.returncode, 0, done.stderr)

    def test_missing_git_has_inventory_error_exit_and_bounded_diagnostic(self):
        self.assert_start_failure(self.invoke(self.bin))

    @unittest.skipUnless(os.name == "posix", "POSIX executable permission fixture")
    def test_git_without_execute_permission_is_inventory_failure(self):
        executable = self.bin / "git"
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o644)
        self.assert_start_failure(self.invoke(self.bin))

    @unittest.skipUnless(os.name == "posix", "POSIX executable format fixture")
    def test_git_with_invalid_executable_format_is_inventory_failure(self):
        executable = self.bin / "git"
        executable.write_text("This is not an executable image.\n", encoding="utf-8")
        executable.chmod(0o755)
        self.assert_start_failure(self.invoke(self.bin))

    @unittest.skipUnless(os.name == "posix", "POSIX shebang interpreter fixture")
    def test_git_with_missing_interpreter_is_inventory_failure(self):
        executable = self.bin / "git"
        interpreter = self.root / "nonexistent-interpreter"
        executable.write_text("#!" + str(interpreter) + "\n", encoding="utf-8")
        executable.chmod(0o755)
        self.assert_start_failure(self.invoke(self.bin))

    @unittest.skipUnless(os.name == "posix", "POSIX directory executable fixture")
    def test_directory_named_git_is_inventory_failure(self):
        (self.bin / "git").mkdir()
        self.assert_start_failure(self.invoke(self.bin))

    def test_real_git_still_checks_tracked_documents(self):
        self.init_repo()
        done = self.invoke()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(done.stderr, "")
        self.assertIn("1 tracked HTML documents checked, 0 missing viewport", done.stdout)
        self.assertEqual(self.page.read_bytes(), PAGE)

    def test_nonrepository_retains_existing_git_exit_diagnostic(self):
        if REAL_GIT is None:
            self.skipTest("real Git is required for the failure control")
        done = self.invoke()
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertEqual(done.stdout, "")
        self.assertIn("INVENTORY FAILED: git ls-files failed with exit", done.stderr)
        self.assertNotIn("could not start", done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        self.assertEqual(self.page.read_bytes(), PAGE)

    def test_restoring_git_recovers_without_modifying_tracked_content(self):
        self.init_repo()
        original_index = (self.repo / ".git" / "index").read_bytes()
        self.assert_start_failure(self.invoke(self.bin))
        recovered = self.invoke()
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        self.assertEqual(recovered.stderr, "")
        self.assertIn("1 tracked HTML documents checked, 0 missing viewport", recovered.stdout)
        self.assertEqual(self.page.read_bytes(), PAGE)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), original_index)


if __name__ == "__main__":
    unittest.main(verbosity=2)
