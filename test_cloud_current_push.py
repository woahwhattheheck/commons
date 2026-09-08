"""Regression coverage for the cloud-current push argument guard."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest

from host.cloud_current_worktree import ForbiddenGit, git, journal_has_forbidden, refuse_forbidden_argv


class CloudCurrentPushTests(unittest.TestCase):
    def test_ordinary_push_arguments_are_returned_unchanged(self):
        for argv in (
            ["push"],
            ["push", "origin", "HEAD:refs/heads/main"],
            ["push", "--dry-run", "origin", "main"],
            ["push", "--porcelain", "origin", "main"],
            ["push", "-u", "origin", "feature"],
            ["push", "origin", "feature/force-review"],
        ):
            with self.subTest(argv=argv):
                before = argv.copy()
                self.assertIs(refuse_forbidden_argv(argv), argv)
                self.assertEqual(argv, before)

    def test_existing_force_push_flags_remain_rejected(self):
        for flag in (
            "-f",
            "--force",
            "--force-with-lease",
            "--force-with-lease=refs/heads/main:abc123",
            "--force-if-includes",
        ):
            for argv in (["push", flag, "origin", "main"],
                         ["push", "origin", "main", flag]):
                with self.subTest(argv=argv):
                    with self.assertRaises(ForbiddenGit):
                        refuse_forbidden_argv(argv)

    def test_other_preservation_rules_are_unchanged(self):
        for argv in (
            [], ["reset", "--hard", "HEAD"], ["reset", "--merge"],
            ["checkout", "HEAD", "--", "file"], ["stash", "drop"],
            ["stash", "pop"], ["clean", "-fd"],
            ["worktree", "remove", "--force", "x"], ["gc"], ["prune"],
        ):
            with self.subTest(argv=argv):
                with self.assertRaises(ForbiddenGit):
                    refuse_forbidden_argv(argv)
        for argv in (["stash", "create"], ["fetch", "origin", "main"],
                     ["worktree", "add", "/tmp/x", "wt/peer/1"]):
            self.assertIs(refuse_forbidden_argv(argv), argv)

    @unittest.skipUnless(shutil.which("git"), "git is required")
    def test_real_push_updates_local_remote_and_preserves_dirty_file(self):
        with tempfile.TemporaryDirectory(prefix="cc-push-") as root:
            root = Path(root)
            work = root / "work"
            remote = root / "remote.git"
            work.mkdir()
            env = os.environ.copy()
            for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
                env.pop(name, None)

            def raw(*args):
                return subprocess.run(
                    ["git", *args], cwd=work, env=env, check=True,
                    capture_output=True, timeout=20,
                ).stdout.strip()

            raw("init", "--bare", str(remote))
            raw("init", "-b", "main")
            raw("config", "commit.gpgsign", "false")
            raw("config", "user.name", "cloud-current-test")
            raw("config", "user.email", "cloud-current@commons.test")
            (work / "tracked.txt").write_bytes(b"committed\n")
            raw("add", "tracked.txt")
            raw("commit", "-m", "initial")
            raw("remote", "add", "origin", str(remote))
            (work / "untracked.txt").write_bytes(b"preserve me\n")
            rc, _, _ = git(["push", "origin", "HEAD:refs/heads/main"], cwd=str(work))
            self.assertEqual(rc, 0)
            self.assertFalse(journal_has_forbidden(str(work)))
            self.assertEqual(raw("--git-dir", str(remote), "rev-parse", "refs/heads/main"), raw("rev-parse", "HEAD"))
            self.assertEqual((work / "untracked.txt").read_bytes(), b"preserve me\n")


if __name__ == "__main__":
    unittest.main()
