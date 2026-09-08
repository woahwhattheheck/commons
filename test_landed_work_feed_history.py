#!/usr/bin/env python3
"""Recent deliveries remain visible across arbitrary first-parent bake runs."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "host" / "landed_work_feed.py"
SPEC = importlib.util.spec_from_file_location("landed_feed_history_target", SOURCE)
feed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(feed)


class LandedWorkHistoryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name)
        self.run_git("init", "-q", "-b", "main")
        self.sequence = 0

    def run_git(self, *args):
        return subprocess.check_output(
            ["git", "-c", "user.name=Feed Fixture", "-c",
             "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
             "-c", "commit.gpgSign=false", *args],
            cwd=self.repo, text=True, stderr=subprocess.PIPE,
        ).strip()

    def commit(self, title, filename="feature.txt"):
        self.sequence += 1
        path = self.repo / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(self.sequence), encoding="utf-8")
        self.run_git("add", "--", filename)
        self.run_git("commit", "-qm", title)
        return self.run_git("rev-parse", "HEAD")

    def bakes(self, count, named=True):
        for _ in range(count):
            self.commit("llms.txt+fresh.md: refresh" if named else "Refresh generated pulse",
                        "fresh.md" if named else "pulse.json")

    def shas(self, limit):
        return [row["sha"] for row in feed.recent_merges(limit, self.repo)]

    def test_delivery_survives_more_than_three_log_pages_of_bakes(self):
        delivery = self.commit("Landed feature #123")
        self.bakes(75)
        self.assertEqual(self.shas(1), [delivery])

    def test_interleaved_deliveries_fill_limit_in_newest_first_order(self):
        older = self.commit("Old delivery #1")
        self.bakes(26)
        middle = self.commit("Middle delivery #2")
        self.bakes(27)
        newest = self.commit("Newest delivery #3")
        self.bakes(28)
        self.assertEqual(self.shas(2), [newest, middle])
        self.assertEqual(self.shas(3), [newest, middle, older])

    def test_path_only_bakes_remain_excluded_across_pages(self):
        delivery = self.commit("Real implementation #4")
        self.bakes(30, named=False)
        self.assertEqual(self.shas(2), [delivery])

    def test_mixed_source_and_generated_commit_remains_visible(self):
        self.commit("Initial implementation")
        (self.repo / "fresh.md").write_text("generated", encoding="utf-8")
        self.run_git("add", "fresh.md")
        delivery = self.commit("Mixed real change #5")
        rows = feed.recent_merges(1, self.repo)
        self.assertEqual(rows[0]["sha"], delivery)
        self.assertEqual(set(rows[0]["paths"]), {"fresh.md", "feature.txt"})
        self.assertEqual(rows[0]["pr"], 5)

    def test_exhausted_history_returns_available_rows_without_duplicates(self):
        first = self.commit("First real item")
        self.bakes(30)
        second = self.commit("Second real item")
        rows = self.shas(10)
        self.assertEqual(rows, [second, first])
        self.assertEqual(len(rows), len(set(rows)))

    def test_all_bake_history_exhausts_to_empty(self):
        self.bakes(50)
        self.assertEqual(self.shas(2), [])

    def test_nonpositive_limit_needs_no_git_history(self):
        with mock.patch.object(feed, "git", side_effect=AssertionError("unexpected Git read")):
            self.assertEqual(feed.recent_merges(0, self.repo), [])
            self.assertEqual(feed.recent_merges(-1, self.repo), [])

    def test_first_parent_history_does_not_double_count_side_branch_commits(self):
        root = self.commit("Initial implementation")
        self.run_git("checkout", "-qb", "feature")
        side = self.commit("Side branch implementation", "side.txt")
        self.run_git("checkout", "-q", "main")
        main = self.commit("Main implementation", "main.txt")
        self.run_git("merge", "--no-ff", "-qm", "Merge pull request #77", "feature")
        merge = self.run_git("rev-parse", "HEAD")
        self.bakes(26)
        rows = feed.recent_merges(3, self.repo)
        self.assertEqual([row["sha"] for row in rows], [merge, main, root])
        self.assertNotIn(side, [row["sha"] for row in rows])
        self.assertEqual(rows[0]["pr"], 77)
        self.assertEqual(rows[0]["paths"], ["side.txt"])

    def test_pagination_uses_one_head_when_new_commits_arrive(self):
        oldest = self.commit("Old original delivery")
        self.bakes(40)
        newest = self.commit("New original delivery")
        original_git = feed.git
        log_calls = []
        arrivals = []

        def moving_head(args, cwd=None):
            result = original_git(args, cwd)
            if args[0] == "log":
                log_calls.append(args)
                if len(log_calls) == 1:
                    arrivals.append(self.commit("Concurrent later delivery"))
            return result

        with mock.patch.object(feed, "git", side_effect=moving_head):
            rows = feed.recent_merges(2, self.repo)
        self.assertGreater(len(log_calls), 1)
        self.assertEqual([row["sha"] for row in rows], [newest, oldest])
        self.assertNotIn(arrivals[0], [row["sha"] for row in rows])
        self.assertTrue(all(newest in args for args in log_calls))

    def test_scan_stops_after_enough_visible_rows(self):
        self.commit("Initial delivery")
        newest = self.commit("Latest delivery")
        with mock.patch.object(feed, "git", wraps=feed.git) as reads:
            self.assertEqual(self.shas(1), [newest])
        self.assertEqual(sum(call.args[0][0] == "log" for call in reads.call_args_list), 1)

    def test_subject_author_and_formatted_delivery_fields_are_preserved(self):
        self.commit("Initial delivery")
        delivery = self.commit("Implement café support (#88)")
        self.bakes(30)
        row = feed.recent_merges(1, self.repo)[0]
        self.assertEqual(row["sha"], delivery)
        self.assertEqual(row["title"], "Implement café support (#88)")
        self.assertEqual(row["author"], "Feed Fixture")
        self.assertEqual(row["harness"], "feed-fixture")
        line = feed.format_line(row)
        self.assertIn("#88 " + delivery[:9], line)
        self.assertIn("paths=feature.txt", line)

    def test_real_cli_reports_delivery_after_dense_bakes_without_sending(self):
        (self.repo / "host").mkdir()
        shutil.copyfile(SOURCE, self.repo / "host" / SOURCE.name)
        (self.repo / "ground").mkdir()
        catalog = {"id": "history-fixture", "ride": "commons-ship-enforcer",
                   "headless_enforcer": "CLAUDE_TAKING", "repos_named_here": 6}
        (self.repo / "ground" / "LANDED_WORK_FEED.json").write_text(json.dumps(catalog), encoding="utf-8")
        self.run_git("add", ".")
        delivery = self.commit("Real CLI delivery #90")
        self.bakes(30)
        result = subprocess.run(
            [sys.executable, str(self.repo / "host" / SOURCE.name), "--json", "--limit", "1"],
            cwd=self.repo, capture_output=True, text=True, timeout=15, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads(result.stdout)
        self.assertEqual(packet["count"], 1)
        self.assertEqual(packet["merges"][0]["sha"], delivery)
        self.assertEqual(packet["sends"], 0)
        self.assertEqual(packet["cash_usd"], 0)
        self.assertEqual(packet["cadence"], "per-merge")
        self.assertEqual(packet["verdict"], "RENDER")

    def test_root_commit_lists_its_actual_paths(self):
        sha = self.commit("Initial delivery", "initial.txt")
        self.assertEqual(feed.paths_of(sha, self.repo), ["initial.txt"])

    def test_git_quoted_and_whitespace_filenames_stay_exact(self):
        self.commit("Initial delivery")
        names = ["café.txt", " leading.txt", "trailing.txt ", "tab\tname.txt",
                 "two\nlines.txt", "carriage\rreturn.txt", '"quoted".txt',
                 "back\\slash.txt", "comma,name.txt", "ends-newline\n"]
        for name in names:
            (self.repo / name).write_text("evidence", encoding="utf-8")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "Delivery with exact filenames")
        sha = self.run_git("rev-parse", "HEAD")
        self.assertEqual(set(feed.paths_of(sha, self.repo)), set(names))

    def test_quote_path_configuration_does_not_change_reported_names(self):
        self.commit("Initial delivery")
        sha = self.commit("Unicode delivery", "récolte-稲.txt")
        for value in ("true", "false"):
            self.run_git("config", "core.quotePath", value)
            self.assertEqual(feed.paths_of(sha, self.repo), ["récolte-稲.txt"])

    def test_rename_and_delete_include_the_affected_paths(self):
        self.commit("Initial delivery", "old.txt")
        self.run_git("mv", "old.txt", "new.txt")
        self.run_git("commit", "-qm", "Rename")
        sha = self.run_git("rev-parse", "HEAD")
        self.assertEqual(set(feed.paths_of(sha, self.repo)), {"old.txt", "new.txt"})
        self.run_git("rm", "-q", "new.txt")
        self.run_git("commit", "-qm", "Delete")
        self.assertEqual(feed.paths_of(self.run_git("rev-parse", "HEAD"), self.repo), ["new.txt"])

    def test_untracked_files_are_not_reported_as_landed(self):
        sha = self.commit("Initial delivery")
        (self.repo / "untracked.txt").write_text("not delivered", encoding="utf-8")
        self.assertEqual(feed.paths_of(sha, self.repo), ["feature.txt"])

    def test_empty_commit_has_no_invented_paths(self):
        self.commit("Initial delivery")
        self.run_git("commit", "--allow-empty", "-qm", "Empty commit")
        self.assertEqual(feed.paths_of(self.run_git("rev-parse", "HEAD"), self.repo), [])

    def test_single_line_display_escapes_controls_without_mutating_paths(self):
        names = ["two\nlines.txt", "carriage\rreturn", "tab\tname", "comma,name", "back\\slash"]
        row = {"repo": feed.REPO, "pr": 88, "sha": "a" * 40,
               "title": "Shipped feature", "harness": "fixture", "paths": names[:]}
        line = feed.format_line(row)
        self.assertEqual(len(line.splitlines()), 1)
        self.assertNotIn("\t", line)
        for name in names:
            self.assertIn(json.dumps(name, ensure_ascii=True), line)
        self.assertEqual(row["paths"], names)

    def test_normal_line_format_is_unchanged(self):
        row = {"repo": feed.REPO, "pr": 91, "sha": "b" * 40,
               "title": "Delivery", "harness": "fixture", "paths": ["src/a.py", "readme.md"]}
        self.assertEqual(feed.format_line(row),
                         "woahwhattheheck/commons #91 bbbbbbbbb Delivery harness=fixture paths=src/a.py,readme.md")

    def test_empty_root_subject_does_not_abort_feed(self):
        (self.repo / "initial.txt").write_text("actual root", encoding="utf-8")
        self.run_git("add", ".")
        self.run_git("commit", "--allow-empty-message", "-qm", "")
        sha = self.run_git("rev-parse", "HEAD")
        rows = feed.recent_merges(1, self.repo)
        self.assertEqual([row["sha"] for row in rows], [sha])
        self.assertEqual(rows[0]["title"], "")
        self.assertEqual(rows[0]["paths"], ["initial.txt"])

    def test_empty_subject_at_history_page_end_remains_visible(self):
        (self.repo / "initial.txt").write_text("actual root", encoding="utf-8")
        self.run_git("add", ".")
        self.run_git("commit", "--allow-empty-message", "-qm", "")
        sha = self.run_git("rev-parse", "HEAD")
        self.bakes(30)
        self.assertEqual(self.shas(1), [sha])

    def test_control_characters_in_subject_are_data_not_record_boundaries(self):
        title = "Implement\talpha\x1ebeta\u2028gamma"
        sha = self.commit(title)
        rows = feed.recent_merges(1, self.repo)
        self.assertEqual(rows[0]["sha"], sha)
        self.assertEqual(rows[0]["title"], title)
        line = feed.format_line(rows[0])
        self.assertEqual(len(line.splitlines()), 1)
        self.assertIn(json.dumps(title, ensure_ascii=True), line)


if __name__ == "__main__":
    unittest.main()
