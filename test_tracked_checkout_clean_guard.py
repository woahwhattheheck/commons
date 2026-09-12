#!/usr/bin/env python3
"""Regression tests for the lexically-last tracked checkout cleanliness guard."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
GUARD = ROOT / "test_zzzzzzzz_tracked_checkout_clean.js"


class TrackedCheckoutCleanGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.node = shutil.which("node")
        cls.git = shutil.which("git")
        if not cls.node or not cls.git:
            raise unittest.SkipTest("node and git are required")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        shutil.copy2(GUARD, self.repo / GUARD.name)
        (self.repo / "tracked.txt").write_text("original\n", encoding="utf-8")
        self._git("init", "-q")
        self._git("config", "user.email", "guard@example.invalid")
        self._git("config", "user.name", "Checkout Guard Test")
        self._git("add", ".")
        self._git("commit", "-qm", "fixture")
        self.checkout_sha = self._git("rev-parse", "HEAD").stdout.strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.git, *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=True,
        )

    def _guard(self, *, expected: str | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["GITHUB_SHA"] = self.checkout_sha if expected is None else expected
        env.pop("CHECKOUT_SHA", None)
        return subprocess.run(
            [self.node, str(self.repo / GUARD.name)],
            cwd=self.repo,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_clean_checkout_passes_and_untracked_scratch_is_ignored(self) -> None:
        (self.repo / "scratch.tmp").write_text("allowed\n", encoding="utf-8")
        completed = self._guard()
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("expected clean postimage", completed.stdout)

    def test_unstaged_tracked_delta_fails_and_names_only_the_path(self) -> None:
        (self.repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        completed = self._guard()
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("modified tracked files", completed.stderr)
        self.assertIn("tracked.txt", completed.stderr)
        self.assertNotIn("changed", completed.stderr)

    def test_staged_tracked_delta_fails(self) -> None:
        (self.repo / "tracked.txt").write_text("staged\n", encoding="utf-8")
        self._git("add", "tracked.txt")
        completed = self._guard()
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("staged tracked-file changes", completed.stderr)
        self.assertIn("tracked.txt", completed.stderr)

    def test_head_move_fails_even_when_new_head_is_clean(self) -> None:
        (self.repo / "tracked.txt").write_text("second commit\n", encoding="utf-8")
        self._git("add", "tracked.txt")
        self._git("commit", "-qm", "move head")
        completed = self._guard(expected=self.checkout_sha)
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("test battery moved HEAD", completed.stderr)
        self.assertIn(self.checkout_sha, completed.stderr)

    def test_git_command_failure_is_fail_closed(self) -> None:
        shutil.rmtree(self.repo / ".git")
        completed = self._guard()
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("HEAD readback failed", completed.stderr)


if __name__ == "__main__":
    unittest.main()
