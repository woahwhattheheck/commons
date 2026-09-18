"""Grouped push flags preserve attached -o data and ordinary Git operations."""
from __future__ import annotations

import itertools
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from host import cloud_current_worktree as cc


class PushClusterTests(unittest.TestCase):
    def test_grouped_force_options_are_refused_before_execution(self):
        for option in ("-uf", "-qvf", "-4f", "-fovalue", "-ufovalue"):
            with self.subTest(option=option), mock.patch.object(cc.subprocess, "run") as run:
                with self.assertRaises(cc.ForbiddenGit):
                    cc.git(["push", option, "origin", "HEAD"])
                run.assert_not_called()

    def test_attached_option_data_is_not_a_force_flag(self):
        for option in ("-oflag", "-uoflag", "-o--force", "-no-force", "-qovalue-f"):
            argv = ["push", option, "origin", "HEAD"]
            with self.subTest(argv=argv):
                before = list(argv)
                self.assertIs(cc.refuse_forbidden_argv(argv), argv)
                self.assertEqual(argv, before)

    def test_option_cluster_matrix(self):
        # Six no-value short flags, prefixes of length 0..3: 259 prefixes.
        for size in range(4):
            for flags in itertools.product("vqun46", repeat=size):
                prefix = "".join(flags)
                for suffix in ("f", "fofeature"):
                    with self.subTest(option="-" + prefix + suffix):
                        with self.assertRaises(cc.ForbiddenGit):
                            cc.refuse_forbidden_argv(["push", "-" + prefix + suffix])
                for suffix in ("of", "o--force"):
                    argv = ["push", "-" + prefix + suffix]
                    with self.subTest(argv=argv):
                        self.assertIs(cc.refuse_forbidden_argv(argv), argv)

    def test_existing_long_options_and_ref_names_are_unchanged(self):
        for option in ("--follow-tags", "--no-force", "--push-option=feature", "refs/heads/force"):
            argv = ["push", "origin", option]
            with self.subTest(argv=argv):
                self.assertIs(cc.refuse_forbidden_argv(argv), argv)
        for option in ("--force", "--force-with-lease", "--force-if-includes"):
            with self.subTest(option=option):
                with self.assertRaises(cc.ForbiddenGit):
                    cc.refuse_forbidden_argv(["push", "origin", option])


class LocalOptionPushTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="cc-push-options-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.remote = self.root / "remote.git"
        self.work = self.root / "work"
        self.work.mkdir()
        cc.git(["init", "--bare", str(self.remote)])
        cc.git(["config", "receive.advertisePushOptions", "true"], cwd=str(self.remote))
        hook = self.remote / "hooks" / "pre-receive"
        hook.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$GIT_PUSH_OPTION_COUNT" "$GIT_PUSH_OPTION_0" > push-options.receipt\n',
            encoding="utf-8",
        )
        hook.chmod(0o700)
        cc.git(["init", "-b", "main"], cwd=str(self.work))
        cc.git(["config", "commit.gpgsign", "false"], cwd=str(self.work))
        cc.git(["config", "user.name", "push-options-test"], cwd=str(self.work))
        cc.git(["config", "user.email", "push-options@commons.test"], cwd=str(self.work))
        (self.work / "tracked.txt").write_bytes(b"original commit\n")
        cc.git(["add", "tracked.txt"], cwd=str(self.work))
        cc.git(["commit", "-m", "fixture"], cwd=str(self.work))
        cc.git(["remote", "add", "origin", str(self.remote)], cwd=str(self.work))
        self.head = cc.head_sha(str(self.work))
        (self.work / "tracked.txt").write_bytes(b"uncommitted tracked bytes\n")
        (self.work / "untracked.txt").write_bytes(b"untracked bytes\n")

    def test_real_attached_push_options_arrive_byte_exact(self):
        for number, (option, value) in enumerate((
            ("-ofeature", "feature"), ("-uoflag", "flag"), ("-o--force", "--force"),
        )):
            with self.subTest(option=option):
                branch = "refs/heads/options-" + str(number)
                cc.git(["push", option, "origin", "HEAD:" + branch], cwd=str(self.work))
                self.assertEqual(cc.rev_sha(str(self.remote), branch), self.head)
                self.assertEqual((self.remote / "push-options.receipt").read_bytes(),
                                 ("1\n" + value + "\n").encode("utf-8"))
                self.assertEqual(cc.head_sha(str(self.work)), self.head)
                self.assertEqual((self.work / "tracked.txt").read_bytes(), b"uncommitted tracked bytes\n")
                self.assertEqual((self.work / "untracked.txt").read_bytes(), b"untracked bytes\n")
        self.assertFalse(cc.journal_has_forbidden(str(self.work)))

    def test_grouped_dry_run_with_option_does_not_update_remote(self):
        cc.git(["push", "-nofeature", "origin", "HEAD:refs/heads/preview"], cwd=str(self.work))
        self.assertEqual(cc.rev_sha(str(self.remote), "refs/heads/preview"), "")
        self.assertFalse((self.remote / "push-options.receipt").exists())
        self.assertEqual(cc.head_sha(str(self.work)), self.head)


if __name__ == "__main__":
    unittest.main()
