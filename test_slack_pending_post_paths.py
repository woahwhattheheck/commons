"""Pending post discovery consumes exact Git filenames, independent of quoting.

Every repository and catalog is temporary. No send, live cursor or network.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))
import commons_slack_full_body_chunk as channel


class PendingPostPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tick = 0
        self.git("init", "-q", "-b", "main")
        self.git("config", "core.quotePath", "true")
        self.write("p/base-post.md")
        self.base = self.commit("Base post")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-c", "user.name=Pending Fixture", "-c",
             "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
             "-c", "commit.gpgSign=false", *args], cwd=self.root,
            env=dict(os.environ, GIT_AUTHOR_DATE=f"{1700000000 + self.tick} +0000",
                     GIT_COMMITTER_DATE=f"{1700000000 + self.tick} +0000"),
            stderr=subprocess.PIPE,
        )

    def write(self, name, text="Actual post body\n"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def commit(self, subject):
        self.tick += 1
        self.git("add", "-A")
        self.git("commit", "-qm", subject)
        return self.git("rev-parse", "HEAD").decode("ascii").strip()

    def pending(self, since=None):
        with patch.object(channel, "ROOT", self.root):
            return channel.pending_posts(self.base if since is None else since)

    def test_quoted_unicode_control_and_punctuation_names_are_exact(self):
        names = ["p/café.md", "p/稲.md", "p/tab\tname.md", "p/new\nline.md",
                 "p/back\\slash.md", 'p/a"quote.md', "p/ space before.md", "p/trailing .md"]
        for name in names:
            self.write(name)
        self.commit("Add exact post names")
        self.assertEqual(set(self.pending()), set(names))
        self.assertTrue(all((self.root / name).is_file() for name in self.pending()))

    def test_quote_path_setting_does_not_change_result(self):
        names = ["p/café.md", "p/tab\tname.md", "p/normal.md"]
        for name in names:
            self.write(name)
        self.commit("Add posts")
        results = []
        for value in ("true", "false"):
            self.git("config", "core.quotePath", value)
            results.append(self.pending())
        self.assertEqual(results[0], results[1])
        self.assertEqual(set(results[0]), set(names))

    def test_range_add_only_and_directory_scope_are_unchanged(self):
        self.write("p/base-post.md", "Modified existing post\n")
        self.write("p/new.md")
        self.write("other/outside.md")
        self.write("p/notes.txt")
        self.write("p/nested/new.md")
        head = self.commit("Mixed changes")
        self.assertEqual(set(self.pending()), {"p/new.md", "p/nested/new.md"})
        self.assertEqual(self.pending(head), [])

    def test_trailing_whitespace_is_not_trimmed_into_a_different_filename(self):
        self.write("p/not-markdown.md ")
        self.write("p/not-markdown.md\n")
        self.write("p/ actual name .md")
        self.commit("Whitespace names")
        self.assertEqual(self.pending(), ["p/ actual name .md"])

    def test_readded_paths_are_unique_and_keep_first_encounter_order(self):
        self.write("p/reused.md")
        self.commit("Add reusable")
        self.write("p/other.md")
        self.commit("Add other")
        (self.root / "p/reused.md").unlink()
        self.commit("Delete reusable")
        self.write("p/reused.md", "Recreated post\n")
        self.commit("Readd reusable")
        self.assertEqual(self.pending(), ["p/reused.md", "p/other.md"])

    def test_ordinary_names_keep_git_encounter_order_across_commits(self):
        self.write("p/first.md")
        self.commit("First")
        self.write("p/third.md")
        self.write("p/second.md")
        self.commit("Later pair")
        self.assertEqual(self.pending(), ["p/second.md", "p/third.md", "p/first.md"])

    def test_untracked_files_and_empty_ranges_do_not_become_pending(self):
        self.write("p/untracked.md")
        self.assertEqual(self.pending(), [])
        self.write("other/tracked.txt")
        self.git("add", "other/tracked.txt")
        self.tick += 1
        self.git("commit", "-qm", "Outside the post directory")
        self.assertEqual(self.pending(), [])

    def test_invalid_revision_still_reports_git_failure(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.pending("missing-revision-which-does-not-exist")

    def test_existing_measurement_consumes_exact_pending_paths_without_sending(self):
        names = ["p/café.md", "p/nested/tab\tname.md"]
        for name in names:
            self.write(name)
        self.commit("Pending Unicode posts")
        catalog = {
            "id": "pending-path-fixture", "ride": "existing test harness", "default_table": "test-channel",
            "last_mirrored_sha": self.base, "keep_unread": {},
            "rule": {"channel_limit": 4000, "remainder_as_thread": True,
                     "id_and_sha_first_line": True, "cursor_advances_only_after_confirmed_post": True,
                     "five_minute_job": True, "login": False, "gate": False, "new_token": False},
        }
        path = self.write("ground/catalog.json", json.dumps(catalog))
        before = path.read_bytes()
        with patch.object(channel, "ROOT", self.root), patch.object(channel, "CATALOG", path):
            packet = channel.measure()
        self.assertEqual(set(packet["pending_posts"]), set(names))
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertEqual(packet["last_mirrored_sha"], self.base)
        self.assertFalse(packet["cursor_advanced"])
        self.assertFalse(packet["confirmed_post"])
        self.assertEqual(packet["sends"], 0)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
