#!/usr/bin/env python3
"""Heads, closures and count custody in feed/github.json.

The rows used to carry number, title, author, draft, created_at and branch.
Those fields cannot show a head moving under a session that reviewed it, a pull
merging while a session prepares to review it, or a count that disagrees with
the listing beside it. Each case below fails on that predecessor.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from host import github_state  # noqa: E402

UNKNOWN = github_state.UNKNOWN
NOW = "2026-09-11T06:00:00Z"
ROOT = os.path.dirname(os.path.abspath(__file__))


def sha(ch):
    return ch * 40


def pull(number, hour, head=None, **extra):
    row = {
        "number": number,
        "title": "pr %d" % number,
        "user": {"login": "peer"},
        "created_at": "2026-09-10T%02d:00:00Z" % hour,
        "updated_at": "2026-09-11T%02d:30:00Z" % (hour % 6),
        "head": {"ref": "branch-%d" % number, "sha": head or sha("a")},
        "base": {"ref": "main"},
    }
    row.update(extra)
    return row


def closed(number, closed_at, merged_at=None, head=None):
    return {
        "number": number,
        "title": "closed %d" % number,
        "user": {"login": "peer"},
        "created_at": "2026-09-10T01:00:00Z",
        "closed_at": closed_at,
        "merged_at": merged_at,
        "head": {"ref": "branch-%d" % number, "sha": head or sha("d")},
        "base": {"ref": "main"},
    }


def listing(n):
    return [pull(12000 + i, i % 24, head="%040x" % (i + 1)) for i in range(n)]


class TestHeadsOnRows(unittest.TestCase):
    def test_every_listed_row_carries_head_update_clock_and_base(self):
        payload = github_state.build([pull(1, 10, head=sha("b"))],
                                     {"open_prs": 1}, NOW, complete=True)
        row = payload["newest_pulls"][0]
        self.assertEqual(row["head_sha"], sha("b"))
        self.assertEqual(row["updated_at"], "2026-09-11T04:30:00Z")
        self.assertEqual(row["base"], "main")
        self.assertEqual(row["branch"], "branch-1")

    def test_only_a_complete_object_id_is_kept(self):
        rows = [pull(1, 1, head="abc123"), pull(2, 2, head="z" * 40),
                pull(3, 3, head="F" * 64), pull(4, 4, head=None)]
        rows[3]["head"] = {"ref": "branch-4"}
        payload = github_state.build(rows, {"open_prs": 4}, NOW, complete=True)
        heads = payload["open_heads"]
        self.assertEqual(heads["1"], UNKNOWN)
        self.assertEqual(heads["2"], UNKNOWN)
        self.assertEqual(heads["3"], "f" * 64)
        self.assertEqual(heads["4"], UNKNOWN)

    def test_a_row_without_head_or_base_reads_unknown(self):
        row = {"number": 5, "title": "bare", "created_at": "2026-09-10T05:00:00Z"}
        payload = github_state.build([row], {"open_prs": 1}, NOW, complete=True)
        got = payload["newest_pulls"][0]
        self.assertEqual(got["head_sha"], UNKNOWN)
        self.assertEqual(got["base"], UNKNOWN)
        self.assertEqual(got["updated_at"], UNKNOWN)


class TestOpenHeads(unittest.TestCase):
    def test_every_open_pull_is_in_the_index_not_only_the_newest(self):
        rows = listing(40)
        payload = github_state.build(rows, {"open_prs": 40}, NOW, complete=True)
        self.assertEqual(len(payload["newest_pulls"]), github_state.NEWEST_N)
        self.assertEqual(len(payload["open_heads"]), 40)
        self.assertEqual(payload["open_heads"]["12000"], "%040x" % 1)
        self.assertEqual(payload["open_heads"]["12039"], "%040x" % 40)

    def test_a_moved_head_changes_the_file_and_a_quiet_cycle_does_not(self):
        rows = listing(20)
        before = github_state.build(rows, {"open_prs": 20}, NOW, complete=True)
        same = github_state.build(listing(20), {"open_prs": 20},
                                  "2026-09-11T07:00:00Z", complete=True)
        self.assertEqual(github_state._dump(before), github_state._dump(same))

        # A pull in the middle of the queue: neither among the ten newest nor
        # the five longest open, so only the index can show its head moving.
        moved = listing(20)
        moved[7]["head"]["sha"] = sha("e")
        after = github_state.build(moved, {"open_prs": 20}, NOW, complete=True)
        shown = [p["number"] for p in after["newest_pulls"] + after["longest_open"]]
        self.assertNotIn(12007, shown)
        self.assertNotEqual(github_state._dump(before), github_state._dump(after))
        self.assertEqual(after["open_heads"]["12007"], sha("e"))

    def test_an_unread_listing_has_no_index_rather_than_an_empty_one(self):
        payload = github_state.build(None, {"open_prs": 3}, NOW, degraded=["pulls"])
        self.assertNotIn("open_heads", payload)
        self.assertEqual(payload["pulls_listed"], UNKNOWN)


class TestRecentlyClosed(unittest.TestCase):
    def test_merged_and_closed_are_named_newest_first_with_the_closing_head(self):
        rows = [
            closed(1, "2026-09-11T01:00:00Z"),
            closed(2, "2026-09-11T03:00:00Z", "2026-09-11T03:00:00Z", sha("c")),
            closed(3, "2026-09-11T02:00:00Z", "2026-09-11T02:00:00Z"),
        ]
        payload = github_state.build([], {"open_prs": 0}, NOW, closed=rows)
        got = payload["recently_closed"]
        self.assertEqual([(r["number"], r["state"]) for r in got],
                         [(2, "MERGED"), (3, "MERGED"), (1, "CLOSED")])
        self.assertEqual(got[0]["head_sha"], sha("c"))
        self.assertEqual(got[0]["merged_at"], "2026-09-11T03:00:00Z")
        self.assertIsNone(got[2]["merged_at"])

    def test_a_malformed_merge_time_is_not_counted_as_a_merge(self):
        rows = [closed(4, "2026-09-11T01:00:00Z", merged_at="soon")]
        got = github_state.build([], {}, NOW, closed=rows)["recently_closed"]
        self.assertEqual(got[0]["state"], "CLOSED")
        self.assertIsNone(got[0]["merged_at"])

    def test_duplicates_and_undated_rows_do_not_reach_the_list(self):
        rows = [closed(5, "2026-09-11T01:00:00Z"), closed(5, "2026-09-11T01:00:00Z"),
                closed(6, ""), closed(7, "whenever"), {"closed_at": NOW}, "noise"]
        got = github_state.build([], {}, NOW, closed=rows)["recently_closed"]
        self.assertEqual([r["number"] for r in got], [5])

    def test_the_list_is_capped_at_the_newest_closures(self):
        rows = [closed(100 + i, "2026-09-10T%02d:00:00Z" % i) for i in range(24)]
        got = github_state.build([], {}, NOW, closed=rows)["recently_closed"]
        self.assertEqual(len(got), github_state.CLOSED_N)
        self.assertEqual(got[0]["number"], 123)

    def test_no_closed_listing_means_no_section(self):
        payload = github_state.build(listing(2), {"open_prs": 2}, NOW, complete=True)
        self.assertNotIn("recently_closed", payload)


class TestCountCustody(unittest.TestCase):
    def test_a_listing_longer_than_the_count_names_the_mismatch(self):
        # The shape a bake published on 2026-09-11: a count of 4 beside a
        # listing of 100 and 87 drafts, with nothing marked degraded.
        rows = listing(100)
        payload = github_state.build(rows, {"open_prs": 4, "source": "search"},
                                     NOW, complete=True)
        self.assertIn("open-count-below-listing", payload["degraded"])
        self.assertEqual(payload["counts"]["open_pull_requests"], 4)
        self.assertEqual(payload["counts_source"], "search")
        self.assertEqual(payload["pulls_listed"], 100)
        self.assertEqual(payload["pulls_listing"], "COMPLETE")

    def test_a_matching_count_has_no_mismatch(self):
        payload = github_state.build(listing(7), {"open_prs": 7, "source": "graphql"},
                                     NOW, complete=True)
        self.assertNotIn("open-count-below-listing", payload["degraded"])
        self.assertEqual(payload["counts_source"], "graphql")

    def test_a_short_listing_stays_partial_and_is_not_called_a_count_mismatch(self):
        payload = github_state.build(listing(3), {"open_prs": 9}, NOW, complete=True)
        self.assertEqual(payload["pulls_listing"], "PARTIAL")
        self.assertNotIn("open-count-below-listing", payload["degraded"])

    def test_a_count_from_an_unnamed_road_reads_unknown_source(self):
        payload = github_state.build(listing(1), {"open_prs": 1}, NOW, complete=True)
        self.assertEqual(payload["counts_source"], UNKNOWN)


class TestCli(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="github-state-heads-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.pulls = os.path.join(self.root, "open.jsonl")
        with open(self.pulls, "w", encoding="utf-8") as fh:
            for row in listing(3):
                fh.write(json.dumps(row) + "\n")

    def run_cli(self, *extra):
        code = github_state.main(["--root", self.root, "--write",
                                  "--pulls", self.pulls, "--pulls-complete",
                                  "--repository", "o/r", "--open-prs", "3",
                                  "--observed-at", NOW] + list(extra))
        self.assertEqual(code, 0)
        with open(os.path.join(self.root, "feed", "github.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def test_a_closed_listing_in_json_lines_is_read(self):
        path = os.path.join(self.root, "closed.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(closed(9, "2026-09-11T02:00:00Z",
                                       "2026-09-11T02:00:00Z")) + "\n")
        out = self.run_cli("--closed", path, "--counts-source", "graphql")
        self.assertEqual(out["recently_closed"][0]["number"], 9)
        self.assertEqual(out["recently_closed"][0]["state"], "MERGED")
        self.assertEqual(out["counts_source"], "graphql")
        self.assertEqual(out["degraded"], [])
        self.assertEqual(len(out["open_heads"]), 3)

    def test_a_missing_closed_file_is_named_not_rendered_as_no_closures(self):
        out = self.run_cli("--closed", os.path.join(self.root, "absent.jsonl"))
        self.assertIn("closed-pulls", out["degraded"])
        self.assertNotIn("recently_closed", out)

    def test_an_unparsable_closed_file_is_named(self):
        path = os.path.join(self.root, "closed.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{\"number\": 1}\nnot json\n")
        out = self.run_cli("--closed", path)
        self.assertIn("closed-pulls", out["degraded"])
        self.assertNotIn("recently_closed", out)

    def test_an_empty_closed_file_is_a_read_with_nothing_closed(self):
        path = os.path.join(self.root, "closed.jsonl")
        open(path, "w", encoding="utf-8").close()
        out = self.run_cli("--closed", path)
        self.assertEqual(out["recently_closed"], [])
        self.assertNotIn("closed-pulls", out["degraded"])


class TestWorkflowAsksForWhatTheModuleReads(unittest.TestCase):
    """The board workflow's projections must carry the fields the module keeps."""

    def setUp(self):
        with open(os.path.join(ROOT, ".github", "workflows", "commons-board.yml"),
                  encoding="utf-8") as fh:
            self.text = fh.read()

    def test_the_open_listing_projects_head_sha_update_clock_and_base(self):
        self.assertIn("repos/$REPO/pulls?state=open", self.text)
        self.assertIn("updated_at", self.text)
        self.assertIn("head:{ref:.head.ref,sha:.head.sha}", self.text)
        self.assertIn("base:{ref:.base.ref}", self.text)

    def test_the_closed_listing_is_read_and_always_handed_to_the_module(self):
        self.assertIn("repos/$REPO/pulls?state=closed&sort=updated", self.text)
        self.assertIn("closed_at,merged_at", self.text)
        self.assertIn("--closed /tmp/closed_pulls.jsonl", self.text)

    def test_open_counts_come_from_the_repository_before_the_search_index(self):
        graphql = self.text.find("pullRequests(states:OPEN){totalCount}")
        search = self.text.find("search/issues?q=repo:$REPO+is:pr+is:open")
        self.assertGreater(graphql, -1)
        self.assertGreater(search, graphql)
        self.assertIn("--counts-source", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
