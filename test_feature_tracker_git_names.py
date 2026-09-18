#!/usr/bin/env python3
"""Real-Git regressions for literal feature paths in sparse working trees."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / "host"))
import feature_tracker as ft


@unittest.skipUnless(shutil.which("git"), "git is required")
class GitNamesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="commons-ft-git-names-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Feature tracker fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgSign", "false")
        self.git("config", "core.quotePath", "true")
        self.git("config", "core.hooksPath", str(Path(self.tmp.name) / "no-hooks"))

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.root), *args], stderr=subprocess.PIPE
        )

    def commit_files(self, paths):
        for rel in paths:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
        self.git("add", "--all")
        self.git("commit", "-qm", "record fixture paths")

    def test_literal_names_with_both_quote_settings(self):
        paths = {"plain.txt", "space name.txt", "café/λ.txt", "line\u00a0space.txt", "unicode\u2028line.txt"}
        self.commit_files(paths)
        for setting in ("true", "false"):
            with self.subTest(quote_path=setting):
                self.git("config", "core.quotePath", setting)
                self.assertEqual(ft.git_names(self.root), paths)

    @unittest.skipIf(os.name == "nt", "Windows disallows these filename characters")
    def test_control_characters_and_backslash_are_literal(self):
        paths = {
            'quote"name.txt', "tab\tname.txt", "line\nname.txt",
            "carriage\rname.txt", "back\\slash.txt", "edge\n", "\nleading.txt",
        }
        self.commit_files(paths)
        for setting in ("true", "false"):
            with self.subTest(quote_path=setting):
                self.git("config", "core.quotePath", setting)
                self.assertEqual(ft.git_names(self.root), paths)

    @unittest.skipUnless(os.name == "posix", "requires byte-valued POSIX filenames")
    def test_non_utf8_filenames_round_trip(self):
        rel = os.fsdecode(b"raw-\xff-name.txt")
        self.commit_files({rel})
        self.assertEqual(ft.git_names(self.root), {rel})
        self.assertEqual(os.fsencode(next(iter(ft.git_names(self.root)))), b"raw-\xff-name.txt")

    def test_union_of_head_and_origin_main(self):
        old = {"shared.txt", "remote-café.txt"}
        self.commit_files(old)
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.git("rm", "--", "remote-café.txt")
        self.commit_files({"local-λ.txt"})
        self.assertEqual(ft.git_names(self.root), old | {"local-λ.txt"})

    def test_sparse_projection_recognizes_files_and_directories(self):
        source = "hidden/café/source.py"
        test_path = "hidden/café/test_source.py"
        self.commit_files({source, test_path, "visible/keep.txt"})
        self.git("sparse-checkout", "init", "--cone")
        self.git("sparse-checkout", "set", "visible")
        self.assertFalse((self.root / source).exists())
        self.assertFalse((self.root / test_path).exists())
        names = ft.git_names(self.root)
        for rel in (source, test_path, "hidden/café"):
            with self.subTest(path=rel):
                self.assertTrue(ft.exists_on_tree(self.root, rel, names))
        self.assertFalse(ft.exists_on_tree(self.root, "hidden/café-missing", names))
        feature = {
            "id": "sparse-literal-path-fixture",
            "claimed_paths": [source, "hidden/café"],
            "test_paths": [test_path],
            "public_entrypoint": source,
        }
        row = ft.derive_feature(feature, [], self.root)
        self.assertEqual(row["claimed_paths_missing"], [])
        self.assertEqual(row["test_paths_missing"], [])
        self.assertEqual(row["source_status"], "SOURCE_BUILT")
        self.assertEqual(row["test_status"], "TESTS_PRESENT")
        self.assertEqual(row["live_status"], "UNMEASURED")

    def test_linked_worktree_gitfile_is_supported(self):
        paths = {"café.txt"}
        self.commit_files(paths)
        linked = Path(self.tmp.name) / "linked"
        self.git("worktree", "add", "--detach", str(linked), "HEAD")
        self.assertTrue((linked / ".git").is_file())
        self.assertEqual(ft.git_names(linked), paths)

    def test_remote_tree_remains_available_without_head(self):
        paths = {"remote-café.txt"}
        self.commit_files(paths)
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.git("symbolic-ref", "HEAD", "refs/heads/unborn-fixture")
        self.assertEqual(ft.git_names(self.root), paths)

    def test_repo_without_commits_returns_empty(self):
        self.assertEqual(ft.git_names(self.root), set())

    def test_nonrepo_returns_empty(self):
        self.assertEqual(ft.git_names(Path(self.tmp.name)), set())


if __name__ == "__main__":
    unittest.main()
