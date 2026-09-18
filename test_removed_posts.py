import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import board_ingest


REMOVED_ID = "slack-1787445882-452089"


class RemovedPostTombstoneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = self.temp.name
        self.posts = os.path.join(self.root, "p")
        os.makedirs(self.posts)
        with open(os.path.join(self.root, "removed_posts.json"), "w", encoding="utf-8") as handle:
            json.dump({"ids": [REMOVED_ID]}, handle)
        self.patchers = [
            mock.patch.object(board_ingest, "ROOT", self.root),
            mock.patch.object(board_ingest, "POSTS", self.posts),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temp.cleanup()

    def test_carrier_replay_does_not_recreate_tombstoned_post(self):
        result = board_ingest.write_post("UNSEATED", "TABLE", REMOVED_ID, "withdrawn")
        self.assertEqual(result, "unchanged")
        self.assertFalse(os.path.exists(os.path.join(self.posts, REMOVED_ID + ".md")))

    def test_purge_runs_on_both_canonical_projections(self):
        for suffix in (".md", ".html"):
            with open(os.path.join(self.posts, REMOVED_ID + suffix), "w", encoding="utf-8") as handle:
                handle.write("stale")
        removed = board_ingest.purge_removed_posts()
        self.assertEqual(set(removed), {"p/" + REMOVED_ID + ".md", "p/" + REMOVED_ID + ".html"})
        self.assertEqual(os.listdir(self.posts), [])

    def test_owner_tombstone_deletions_are_not_restored(self):
        deleted = "p/" + REMOVED_ID + ".md"
        with mock.patch.object(board_ingest, "_git", return_value=SimpleNamespace(stdout=deleted + "\n")) as git:
            held = board_ingest._unstage_record_deletes({})
        self.assertEqual(held, [])
        git.assert_called_once()

    def test_unrelated_record_deletion_is_still_restored(self):
        deleted = "p/ordinary-record.md"
        calls = []

        def fake_git(args, env):
            calls.append(args)
            return SimpleNamespace(stdout=deleted + "\n" if len(calls) == 1 else "")

        with mock.patch.object(board_ingest, "_git", side_effect=fake_git):
            held = board_ingest._unstage_record_deletes({})
        self.assertEqual(held, [deleted])
        self.assertEqual(calls[1][:5], ["reset", "-q", "HEAD", "--", deleted])
        self.assertEqual(calls[2][:5], ["checkout", "-q", "HEAD", "--", deleted])


if __name__ == "__main__":
    unittest.main()
