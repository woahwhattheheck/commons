#!/usr/bin/env python3
"""Ordinary cloud-current pushes reach Git; explicit force options do not."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parent / "host" / "cloud_current_worktree.py"
SPEC = importlib.util.spec_from_file_location("cloud_current_push_subject", SOURCE)
cc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cc)


class PushArgumentsTests(unittest.TestCase):
    def test_ordinary_push_arguments_are_returned_unchanged(self):
        cases = [
            ["push"],
            ["push", "origin", "HEAD"],
            ["push", "--dry-run", "origin", "HEAD"],
            ["push", "-u", "origin", "HEAD:refs/heads/topic"],
            ["push", "--follow-tags", "origin", "HEAD"],
            ["push", "--atomic", "origin", "HEAD"],
            ["push", "--no-force", "origin", "HEAD"],
            ["push", "origin", "refs/heads/force:refs/heads/force"],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                self.assertIs(cc.refuse_forbidden_argv(argv), argv)

    def test_explicit_force_options_still_raise(self):
        for option in (
            "-f", "-uf", "--force", "--force-with-lease",
            "--force-with-lease=refs/heads/main", "--force-with-lease=refs/heads/main:",
            "--force-if-includes",
        ):
            with self.subTest(option=option):
                with self.assertRaises(cc.ForbiddenGit):
                    cc.refuse_forbidden_argv(["push", option, "origin", "HEAD"])

    def test_force_options_after_remote_still_raise(self):
        with self.assertRaises(cc.ForbiddenGit):
            cc.refuse_forbidden_argv(["push", "origin", "--force", "HEAD"])

    def test_non_push_commands_are_unchanged(self):
        for argv in (["fetch", "origin", "main"], ["stash", "create"],
                     ["diff", "--name-only"], ["worktree", "add", "/tmp/example", "topic"]):
            with self.subTest(argv=argv):
                self.assertIs(cc.refuse_forbidden_argv(argv), argv)

    def test_existing_destructive_command_checks_are_unchanged(self):
        for argv in (["reset", "--hard", "HEAD"], ["checkout", "HEAD", "--", "file"],
                     ["stash", "pop"], ["clean", "-fd"],
                     ["worktree", "remove", "--force", "example"], ["gc"], ["prune"]):
            with self.subTest(argv=argv):
                with self.assertRaises(cc.ForbiddenGit):
                    cc.refuse_forbidden_argv(argv)

    def test_force_refusal_happens_before_subprocess(self):
        with mock.patch.object(cc.subprocess, "run") as run:
            with self.assertRaises(cc.ForbiddenGit):
                cc.git(["push", "--force", "origin", "HEAD"])
        run.assert_not_called()


class LocalPushTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="cc-push-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.remote = self.root / "remote.git"
        self.work = self.root / "work"
        self.work.mkdir()
        cc.git(["init", "--bare", str(self.remote)])
        cc.git(["init", "-b", "main"], cwd=str(self.work))
        cc.git(["config", "user.email", "peer@commons.test"], cwd=str(self.work))
        cc.git(["config", "user.name", "cloud-current-push-test"], cwd=str(self.work))
        cc.git(["remote", "add", "origin", str(self.remote)], cwd=str(self.work))
        self._commit("first\n")

    def _commit(self, body):
        (self.work / "tracked.txt").write_text(body, encoding="utf-8")
        cc.git(["add", "tracked.txt"], cwd=str(self.work))
        cc.git(["commit", "-m", "fixture change"], cwd=str(self.work))
        return cc.head_sha(str(self.work))

    def test_normal_push_reaches_local_remote_and_preserves_dirt(self):
        dirt = self.work / "uncommitted.txt"
        dirt.write_bytes(b"preserve this work\n")
        before = cc.head_sha(str(self.work))
        rc, _, _ = cc.git(["push", "origin", "HEAD:refs/heads/topic"], cwd=str(self.work))
        self.assertEqual(rc, 0)
        self.assertEqual(cc.rev_sha(str(self.remote), "refs/heads/topic"), before)
        self.assertEqual(cc.head_sha(str(self.work)), before)
        self.assertEqual(dirt.read_bytes(), b"preserve this work\n")
        self.assertFalse(cc.journal_has_forbidden(str(self.work)))
        journal = self.work / cc.JOURNAL_FILE
        rows = [json.loads(line) for line in journal.read_text().splitlines()]
        self.assertIn(["push", "origin", "HEAD:refs/heads/topic"], [row["argv"] for row in rows])

    def test_dry_run_does_not_create_remote_ref(self):
        rc, _, _ = cc.git(["push", "--dry-run", "origin", "HEAD:refs/heads/preview"], cwd=str(self.work))
        self.assertEqual(rc, 0)
        self.assertEqual(cc.rev_sha(str(self.remote), "refs/heads/preview"), "")

    def test_subsequent_fast_forward_push(self):
        cc.git(["push", "origin", "HEAD:refs/heads/topic"], cwd=str(self.work))
        next_sha = self._commit("second\n")
        cc.git(["push", "origin", "HEAD:refs/heads/topic"], cwd=str(self.work))
        self.assertEqual(cc.rev_sha(str(self.remote), "refs/heads/topic"), next_sha)


if __name__ == "__main__":
    unittest.main()
