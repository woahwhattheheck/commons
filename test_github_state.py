#!/usr/bin/env python3
"""Contract for host/github_state.py — repository state as a static file.

The module self-test covers normalisation and the UNKNOWN rules. This covers the
disk road: writing, the unchanged-state guard that keeps `unchanged_since`
meaningful, and behaviour when the pull listing cannot be read.
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
COUNTS = {"repository": "o/r", "open_prs": 106, "open_issues": 3,
          "runs_queued": 2275, "runs_in_progress": 18}


def pulls(n=3, hour=10):
    return [
        {"number": 100 + i, "title": "pr %d" % i, "user": {"login": "who"},
         "created_at": "2026-09-10T%02d:00:00Z" % (hour + i),
         "head": {"ref": "branch-%d" % i}}
        for i in range(n)
    ]


class TempRepo(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="github-state-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def out(self):
        path = os.path.join(self.root, "feed", "github.json")
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)


class TestSelfContract(unittest.TestCase):
    def test_module_self_test_passes(self):
        self.assertEqual(github_state.self_test(), 0)


class TestWrite(TempRepo):
    def test_writes_counts_and_listings(self):
        payload = github_state.build(pulls(), COUNTS, "2026-09-10T21:00:00Z")
        self.assertTrue(github_state.write(self.root, payload,
                                           "2026-09-10T21:00:00Z"))
        out = self.out()
        self.assertEqual(out["counts"]["open_pull_requests"], 106)
        self.assertEqual(out["counts"]["runs_queued"], 2275)
        self.assertEqual(out["unchanged_since"], "2026-09-10T21:00:00Z")
        self.assertEqual([p["number"] for p in out["newest_pulls"]],
                         [102, 101, 100])

    def test_unchanged_state_leaves_the_file_completely_alone(self):
        payload = github_state.build(pulls(), COUNTS, "2026-09-10T21:00:00Z")
        github_state.write(self.root, payload, "2026-09-10T21:00:00Z")
        first = self.out()
        again = github_state.build(pulls(), COUNTS, "2026-09-10T22:00:00Z")
        self.assertFalse(github_state.write(self.root, again,
                                            "2026-09-10T22:00:00Z"))
        self.assertEqual(self.out(), first)
        self.assertEqual(self.out()["unchanged_since"], "2026-09-10T21:00:00Z")

    def test_a_changed_count_rewrites_and_restamps(self):
        github_state.write(
            self.root,
            github_state.build(pulls(), COUNTS, "2026-09-10T21:00:00Z"),
            "2026-09-10T21:00:00Z")
        moved = dict(COUNTS, runs_queued=2400)
        self.assertTrue(github_state.write(
            self.root,
            github_state.build(pulls(), moved, "2026-09-10T22:00:00Z"),
            "2026-09-10T22:00:00Z"))
        out = self.out()
        self.assertEqual(out["counts"]["runs_queued"], 2400)
        self.assertEqual(out["unchanged_since"], "2026-09-10T22:00:00Z")


class TestHonesty(TempRepo):
    def test_a_missing_count_is_unknown_not_zero(self):
        payload = github_state.build(pulls(), {"repository": "o/r"},
                                     "2026-09-10T21:00:00Z")
        self.assertEqual(payload["counts"]["open_pull_requests"], UNKNOWN)
        self.assertEqual(payload["counts"]["runs_queued"], UNKNOWN)

    def test_a_real_zero_stays_zero(self):
        payload = github_state.build([], dict(COUNTS, open_prs=0),
                                     "2026-09-10T21:00:00Z")
        self.assertEqual(payload["counts"]["open_pull_requests"], 0)
        self.assertEqual(payload["pulls_listed"], 0)
        self.assertEqual(payload["newest_pulls"], [])

    def test_an_unreadable_listing_is_named_not_rendered_as_empty(self):
        payload = github_state.build(None, COUNTS, "2026-09-10T21:00:00Z",
                                     degraded=["pulls"])
        self.assertEqual(payload["degraded"], ["pulls"])
        self.assertEqual(payload["pulls_listed"], UNKNOWN)
        self.assertNotIn("newest_pulls", payload)
        self.assertEqual(payload["counts"]["runs_queued"], 2275)

    def test_queue_depth_needs_both_numbers(self):
        self.assertEqual(
            github_state.build(None, dict(COUNTS, runs_in_progress=None),
                               "2026-09-10T21:00:00Z")["queue_depth_per_runner"],
            UNKNOWN)
        self.assertEqual(
            github_state.build(None, dict(COUNTS, runs_in_progress=0),
                               "2026-09-10T21:00:00Z")["queue_depth_per_runner"],
            UNKNOWN)

    def test_an_undated_pull_is_counted_but_not_ordered(self):
        rows = pulls(2) + [{"number": 999, "title": "no clock",
                            "user": {"login": "who"}}]
        payload = github_state.build(rows, COUNTS, "2026-09-10T21:00:00Z")
        self.assertEqual(payload["pulls_listed"], 3)
        numbers = [p["number"] for p in payload["newest_pulls"]]
        self.assertNotIn(999, numbers)
        self.assertEqual(len(numbers), 2)

    def test_a_missing_author_reads_unknown(self):
        payload = github_state.build([{"number": 1, "title": "t",
                                       "created_at": "2026-09-10T20:00:00Z"}],
                                     COUNTS, "2026-09-10T21:00:00Z")
        self.assertEqual(payload["newest_pulls"][0]["author"], UNKNOWN)
        self.assertEqual(payload["newest_pulls"][0]["branch"], UNKNOWN)


class TestTimeIsNotBakedIn(unittest.TestCase):
    def test_no_observation_relative_field_reaches_the_payload(self):
        early = github_state.build(pulls(), COUNTS, "2026-09-10T21:00:00Z")
        late = github_state.build(pulls(), COUNTS, "2026-09-12T09:00:00Z")
        self.assertEqual(early, late)
        self.assertNotIn("age_hours", early["newest_pulls"][0])
        self.assertEqual(early["newest_pulls"][0]["created_at"],
                         "2026-09-10T12:00:00Z")

    def test_a_malformed_creation_is_listed_but_never_ordered(self):
        rows = pulls(2) + [{"number": 999, "title": "broken clock",
                            "user": {"login": "a"}, "created_at": "whenever"}]
        payload = github_state.build(rows, COUNTS, "2026-09-10T21:00:00Z",
                                     complete=True)
        self.assertEqual(payload["pulls_listed"], 3)
        self.assertEqual(payload["undatable_pulls"], [999])
        self.assertNotIn(999, [p["number"] for p in payload["newest_pulls"]])
        self.assertNotIn(999, [p["number"] for p in payload["longest_open"]])
        self.assertEqual(payload["newest_pulls"][0]["number"], 101)


class TestListingCoverage(TempRepo):
    """The oldest row of a newest-first page is not the longest-open PR."""

    def test_a_listing_shorter_than_the_open_count_is_partial(self):
        # 100 newest rows against 114 counted open, exactly the reviewed case.
        rows = pulls(100, hour=0)
        payload = github_state.build(rows, dict(COUNTS, open_prs=114),
                                     "2026-09-10T21:00:00Z")
        self.assertEqual(payload["pulls_listing"], "PARTIAL")
        self.assertNotIn("longest_open", payload)
        self.assertIn("pulls-partial", payload["degraded"])
        self.assertEqual(len(payload["newest_pulls"]), github_state.NEWEST_N)

    def test_a_paginated_listing_is_complete_and_names_the_oldest(self):
        rows = pulls(114, hour=0)
        payload = github_state.build(rows, dict(COUNTS, open_prs=114),
                                     "2026-09-10T21:00:00Z", complete=True)
        self.assertEqual(payload["pulls_listing"], "COMPLETE")
        self.assertEqual(payload["longest_open"][0]["number"], 100)
        self.assertNotIn("pulls-partial", payload["degraded"])

    def test_a_listing_at_least_the_counted_total_is_complete_without_the_flag(self):
        # The search count lags; a listing longer than it is still whole.
        payload = github_state.build(pulls(5), dict(COUNTS, open_prs=4),
                                     "2026-09-10T21:00:00Z")
        self.assertEqual(payload["pulls_listing"], "COMPLETE")
        self.assertIn("longest_open", payload)

    def test_no_count_and_no_flag_is_unknown_coverage(self):
        payload = github_state.build(pulls(3), {"repository": "o/r"},
                                     "2026-09-10T21:00:00Z")
        self.assertEqual(payload["pulls_listing"], UNKNOWN)
        self.assertNotIn("longest_open", payload)
        self.assertIn("pulls-coverage-unknown", payload["degraded"])

    def test_a_row_repeated_across_pages_is_counted_once(self):
        rows = pulls(3) + pulls(3)[1:]
        payload = github_state.build(rows, dict(COUNTS, open_prs=3),
                                     "2026-09-10T21:00:00Z", complete=True)
        self.assertEqual(payload["pulls_listed"], 3)
        self.assertEqual([p["number"] for p in payload["newest_pulls"]],
                         [102, 101, 100])

    def test_the_cli_reads_json_lines_from_a_paginated_call(self):
        path = os.path.join(self.root, "pulls.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for row in pulls(3):
                fh.write(json.dumps(row) + "\n")
        code = github_state.main([
            "--root", self.root, "--write", "--pulls", path, "--pulls-complete",
            "--repository", "o/r", "--open-prs", "3",
            "--observed-at", "2026-09-10T21:00:00Z"])
        self.assertEqual(code, 0)
        out = self.out()
        self.assertEqual(out["pulls_listed"], 3)
        self.assertEqual(out["pulls_listing"], "COMPLETE")
        self.assertEqual(out["longest_open"][0]["number"], 100)

    def test_the_cli_names_an_unparsable_listing(self):
        path = os.path.join(self.root, "pulls.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"number": 1}\nnot json\n')
        github_state.main(["--root", self.root, "--write", "--pulls", path,
                           "--observed-at", "2026-09-10T21:00:00Z"])
        out = self.out()
        self.assertEqual(out["degraded"], ["pulls"])
        self.assertEqual(out["pulls_listed"], UNKNOWN)


class TestAtomicWrite(TempRepo):
    def test_a_failed_write_leaves_the_previous_bytes_exactly(self):
        github_state.write(
            self.root, github_state.build(pulls(), COUNTS, "2026-09-10T21:00:00Z"),
            "2026-09-10T21:00:00Z")
        path = os.path.join(self.root, "feed", "github.json")
        with open(path, "rb") as fh:
            before = fh.read()

        real_replace = os.replace

        def refuse(src, dst):
            raise OSError("disk went away mid-publish")

        os.replace = refuse
        try:
            with self.assertRaises(OSError):
                github_state.write(
                    self.root,
                    github_state.build(pulls(), dict(COUNTS, runs_queued=9),
                                       "2026-09-10T22:00:00Z"),
                    "2026-09-10T22:00:00Z")
        finally:
            os.replace = real_replace

        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), before)
        leftovers = [n for n in os.listdir(os.path.dirname(path))
                     if n.endswith(".tmp")]
        self.assertEqual(leftovers, [], "the temporary file is cleaned up")

    def test_a_successful_write_leaves_no_temporary_file(self):
        github_state.write(
            self.root, github_state.build(pulls(), COUNTS, "2026-09-10T21:00:00Z"),
            "2026-09-10T21:00:00Z")
        folder = os.path.join(self.root, "feed")
        self.assertEqual(sorted(os.listdir(folder)), ["github.json"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
