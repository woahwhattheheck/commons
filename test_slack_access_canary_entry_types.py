#!/usr/bin/env python3
"""Real filesystem regressions for the local Slack-post landing canary.

This validates local entry identity/type, not Git ancestry or Slack delivery.
No network, provider calls, or existing posts are needed or changed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import slack_access_canary as canary


TS = "1787630616.892789"
MIRROR = "slack-1787630616-892789"
DECLARED = "sol-canary-entry-fixture"
ROOT = Path(__file__).resolve().parent


class LocalPostEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.posts = self.root / "p"
        self.posts.mkdir()

    def measure(self, declared_id=None, slack_write=True):
        return canary.measure_posts_dir(
            TS, str(self.posts), declared_id=declared_id, slack_write=slack_write
        )

    def assert_not_landed(self, row, state="NOT_LANDED"):
        self.assertIs(row["measured"], True)
        self.assertIs(row["file_on_head"], False)
        self.assertEqual(row["landed_id"], "")
        self.assertEqual(canary.classify(row)["state"], state)

    def make_link(self, target, name=None, directory=False):
        link = self.posts / ((name or MIRROR) + ".md")
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (NotImplementedError, OSError) as exc:
            self.skipTest("symlink creation unavailable: %s" % exc)
        return link

    def run_cli(self, *extra):
        result = subprocess.run(
            [sys.executable, str(ROOT / "host/slack_access_canary.py"),
             "--ts", TS, "--posts-dir", str(self.posts), *extra],
            text=True, capture_output=True, timeout=10, check=False,
        )
        return result, json.loads(result.stdout)

    def test_existing_self_test(self):
        self.assertTrue(canary._self_test())

    def test_regular_mirror_file_is_integrated(self):
        (self.posts / (MIRROR + ".md")).write_text("receipt\n", encoding="utf-8")
        row = self.measure()
        self.assertIs(row["file_on_head"], True)
        self.assertEqual(row["landed_id"], MIRROR)
        self.assertEqual(canary.classify(row)["state"], "INTEGRATED")
        self.assertEqual(row["posts_dir"], str(self.posts))
        self.assertEqual(row["candidates"], [MIRROR])

    def test_zero_byte_regular_file_keeps_existing_presence_contract(self):
        (self.posts / (MIRROR + ".md")).touch()
        self.assertIs(self.measure()["file_on_head"], True)

    def test_declared_file_is_integrated(self):
        (self.posts / (DECLARED + ".md")).touch()
        row = self.measure(DECLARED)
        self.assertEqual(row["landed_id"], DECLARED)
        self.assertEqual(row["declared_id"], DECLARED)
        self.assertEqual(row["candidates"], [DECLARED, MIRROR])

    def test_declared_id_ending_html_matches_its_exact_md_file(self):
        declared = DECLARED + ".html"
        (self.posts / (declared + ".md")).touch()
        self.assertEqual(self.measure(declared)["landed_id"], declared)

    def test_declared_id_ending_md_matches_its_exact_md_file(self):
        declared = DECLARED + ".md"
        (self.posts / (declared + ".md")).touch()
        self.assertEqual(self.measure(declared)["landed_id"], declared)

    def test_declared_regular_file_has_priority_over_regular_mirror(self):
        for post_id in (MIRROR, DECLARED):
            (self.posts / (post_id + ".md")).touch()
        self.assertEqual(self.measure(DECLARED)["landed_id"], DECLARED)

    def test_mirror_named_directory_is_not_a_post(self):
        (self.posts / (MIRROR + ".md")).mkdir()
        self.assert_not_landed(self.measure())

    def test_declared_named_directory_is_not_a_post(self):
        (self.posts / (DECLARED + ".md")).mkdir()
        self.assert_not_landed(self.measure(DECLARED))

    def test_declared_directory_does_not_shadow_regular_mirror(self):
        (self.posts / (DECLARED + ".md")).mkdir()
        (self.posts / (MIRROR + ".md")).touch()
        self.assertEqual(self.measure(DECLARED)["landed_id"], MIRROR)

    def test_symlink_to_regular_file_is_not_a_post(self):
        target = self.root / "outside.md"
        target.write_text("not a post in p\n", encoding="utf-8")
        self.make_link(target)
        self.assert_not_landed(self.measure())

    def test_dangling_symlink_is_not_a_post(self):
        self.make_link(self.root / "missing.md")
        self.assert_not_landed(self.measure())

    def test_symlink_to_directory_is_not_a_post(self):
        target = self.root / "outside-dir"
        target.mkdir()
        self.make_link(target, directory=True)
        self.assert_not_landed(self.measure())

    def test_declared_symlink_does_not_shadow_regular_mirror(self):
        target = self.root / "outside.md"
        target.touch()
        self.make_link(target, name=DECLARED)
        (self.posts / (MIRROR + ".md")).touch()
        self.assertEqual(self.measure(DECLARED)["landed_id"], MIRROR)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "named pipes unavailable")
    def test_fifo_is_not_a_post_and_is_never_opened(self):
        os.mkfifo(self.posts / (MIRROR + ".md"))
        self.assert_not_landed(self.measure())

    def test_whitespace_prefixed_filename_is_not_the_exact_post(self):
        (self.posts / (" " + MIRROR + ".md")).touch()
        self.assert_not_landed(self.measure())

    def test_extra_html_suffix_is_not_the_exact_post(self):
        (self.posts / (MIRROR + ".html.md")).touch()
        self.assert_not_landed(self.measure())

    def test_html_projection_is_not_a_local_md_post(self):
        (self.posts / (MIRROR + ".html")).touch()
        self.assert_not_landed(self.measure())

    def test_nested_post_is_not_a_direct_p_entry(self):
        nested = self.posts / "archive"
        nested.mkdir()
        (nested / (MIRROR + ".md")).touch()
        self.assert_not_landed(self.measure())

    def test_empty_directory_is_a_complete_non_landed_measurement(self):
        self.assert_not_landed(self.measure())

    def test_missing_posts_directory_stays_unmeasured(self):
        self.posts.rmdir()
        row = self.measure()
        self.assertIs(row["measured"], False)
        self.assertIn("posts dir missing:", row["error"])
        self.assertEqual(canary.classify(row)["state"], "UNMEASURED")

    def test_file_instead_of_posts_directory_stays_unmeasured(self):
        self.posts.rmdir()
        self.posts.touch()
        self.assertEqual(canary.classify(self.measure())["state"], "UNMEASURED")

    def test_directory_with_no_write_is_claimed_not_integrated(self):
        (self.posts / (MIRROR + ".md")).mkdir()
        self.assert_not_landed(self.measure(slack_write=False), "CLAIMED")

    def test_regular_file_with_no_write_stays_integrated(self):
        (self.posts / (MIRROR + ".md")).touch()
        row = self.measure(slack_write=False)
        self.assertIs(row["slack_write"], False)
        self.assertEqual(canary.classify(row)["state"], "INTEGRATED")

    def test_explicit_symlinked_posts_root_remains_supported(self):
        actual = self.root / "actual-posts"
        self.posts.rename(actual)
        try:
            self.posts.symlink_to(actual, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            self.skipTest("symlink creation unavailable: %s" % exc)
        (actual / (MIRROR + ".md")).touch()
        self.assertIs(self.measure()["file_on_head"], True)

    def test_pure_listing_html_normalization_is_unchanged(self):
        row = canary.measure_from_listing(TS, [MIRROR + ".html"])
        self.assertIs(row["file_on_head"], True)

    def test_cli_directory_is_not_landed(self):
        (self.posts / (MIRROR + ".md")).mkdir()
        result, payload = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["state"], "NOT_LANDED")
        self.assertIs(payload["file_on_head"], False)

    def test_cli_regular_file_is_integrated(self):
        (self.posts / (MIRROR + ".md")).touch()
        result, payload = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["state"], "INTEGRATED")

    def test_cli_no_write_directory_is_claimed(self):
        (self.posts / (MIRROR + ".md")).mkdir()
        result, payload = self.run_cli("--no-write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["state"], "CLAIMED")

    def test_cli_missing_directory_returns_json_and_exit_two(self):
        self.posts.rmdir()
        result, payload = self.run_cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(payload["state"], "UNMEASURED")


if __name__ == "__main__":
    unittest.main()
