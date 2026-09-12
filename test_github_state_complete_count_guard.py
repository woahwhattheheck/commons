#!/usr/bin/env python3
"""Regression for successful pagination that is still coverage-short after dedupe."""

import unittest

from host import github_state


def row(number, hour):
    return {
        "number": number,
        "title": f"pr {number}",
        "user": {"login": "peer"},
        "created_at": f"2026-09-11T{hour:02d}:00:00Z",
        "head": {"ref": f"branch-{number}"},
    }


class TestCompletePaginationCountGuard(unittest.TestCase):
    def test_successful_pagination_cannot_override_short_unique_listing(self):
        # Simulate a page-boundary race: PR 2 is repeated while the independently
        # observed count says four PRs are open. The pagination command may have
        # exited successfully, but after dedupe only three unique rows remain.
        rows = [row(1, 1), row(2, 2), row(3, 3), row(2, 2)]
        payload = github_state.build(
            rows,
            {"repository": "o/r", "open_prs": 4},
            "2026-09-11T05:00:00Z",
            complete=True,
        )
        self.assertEqual(payload["pulls_listed"], 3)
        self.assertEqual(payload["pulls_listing"], "PARTIAL")
        self.assertNotIn("longest_open", payload)
        self.assertIn("pulls-partial", payload["degraded"])

    def test_successful_pagination_with_matching_unique_count_is_complete(self):
        rows = [row(1, 1), row(2, 2), row(3, 3), row(2, 2)]
        payload = github_state.build(
            rows,
            {"repository": "o/r", "open_prs": 3},
            "2026-09-11T05:00:00Z",
            complete=True,
        )
        self.assertEqual(payload["pulls_listing"], "COMPLETE")
        self.assertIn("longest_open", payload)

    def test_successful_pagination_without_independent_count_remains_usable(self):
        rows = [row(1, 1), row(2, 2), row(3, 3)]
        payload = github_state.build(
            rows,
            {"repository": "o/r"},
            "2026-09-11T05:00:00Z",
            complete=True,
        )
        self.assertEqual(payload["pulls_listing"], "COMPLETE")
        self.assertIn("longest_open", payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
