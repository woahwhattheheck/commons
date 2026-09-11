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
        payload = github_state.build(rows, COUNTS, "2026-09-10T21:00:00Z")
        self.assertEqual(payload["pulls_listed"], 3)
        self.assertEqual(payload["undatable_pulls"], [999])
        self.assertNotIn(999, [p["number"] for p in payload["newest_pulls"]])
        self.assertNotIn(999, [p["number"] for p in payload["longest_open"]])
        self.assertEqual(payload["newest_pulls"][0]["number"], 101)


if __name__ == "__main__":
    unittest.main(verbosity=2)
