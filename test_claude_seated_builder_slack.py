#!/usr/bin/env python3
"""A11 leftover: named Slack seated-builder census. Never silent 0."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_seated_builder_slack import (
    CALIBRATION,
    CORNER_NAME,
    DO_NOT_REMINT,
    DO_NOT_REWRITE,
    DO_NOT_WRITE,
    KEYWORD_QUERIES,
    PEER_CHECK,
    QUOTED_QUERIES,
    SEARCH_SPACE,
    classify,
    measure_from_rows,
    measure_root,
    query_row,
    self_test,
)


def _complete(**overrides):
    facts = {
        "calibration_ok": True,
        "calibration_hits": list(CALIBRATION),
        "no_auth": True,
        "no_gate": True,
        "posting": "OPEN",
        "quoted": [
            query_row(QUOTED_QUERIES[0], 0, "quoted"),
            query_row(QUOTED_QUERIES[1], 0, "quoted"),
        ],
        "keyword": [
            query_row(KEYWORD_QUERIES[0], 3, "keyword"),
            query_row(KEYWORD_QUERIES[1], 3, "keyword"),
        ],
        "wrote_corner": False,
        "treated_empty_as_clear": False,
    }
    facts.update(overrides)
    return measure_from_rows(facts)


class TestClaudeSeatedBuilderSlack(unittest.TestCase):
    def test_self_test_ok(self):
        self.assertEqual(self_test(), "ok")

    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertEqual(row["z"], "FINDER-FAILED")
        self.assertIn("Never 0", row["note"])
        self.assertNotEqual(row.get("count"), 0)

    def test_failed_calibration_is_instrument_failure(self):
        row = classify(_complete(calibration_ok=False, calibration_hits=[]))
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertEqual(row["z"], "FINDER-FAILED")
        self.assertIn("instrument failure", row["note"])

    def test_closed_door_is_discarded(self):
        row = classify(_complete(no_auth=False))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("closed the door", row["note"])

    def test_writing_corner_is_the_failure_mode(self):
        row = classify(_complete(wrote_corner=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertEqual(row["z"], "HIT")
        self.assertIn("failure", row["note"].lower())

    def test_empty_quoted_search_is_finder_unverified_not_clear(self):
        row = query_row(QUOTED_QUERIES[0], 0, "quoted")
        self.assertEqual(row["state"], "FINDER-UNVERIFIED")
        self.assertEqual(row["count"], 0)
        self.assertIn("never silent 0", row["note"])
        self.assertFalse(row["permission"])

    def test_empty_treated_as_clear_is_refused(self):
        row = classify(_complete(treated_empty_as_clear=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("CZ-03", row["note"])

    def test_keyword_hits_are_not_permission(self):
        row = query_row(KEYWORD_QUERIES[0], 3, "keyword")
        self.assertEqual(row["state"], "SEARCH_HIT")
        self.assertEqual(row["count"], 3)
        self.assertFalse(row["permission"])
        self.assertIn("not a seated-builder", row["note"])

    def test_missing_count_is_finder_unverified(self):
        row = query_row(QUOTED_QUERIES[1], None, "quoted")
        self.assertEqual(row["state"], "FINDER-UNVERIFIED")
        self.assertIsNone(row["count"])

    def test_non_integer_count_is_finder_failed(self):
        row = query_row(QUOTED_QUERIES[0], "nope", "quoted")
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertIsNone(row["count"])

    def test_this_seat_recorded_sample_is_integrated(self):
        row = classify(_complete())
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["z"]["quoted"], "FINDER-UNVERIFIED,FINDER-UNVERIFIED")
        self.assertEqual(row["z"]["keyword"], "SEARCH_HIT,SEARCH_HIT")
        self.assertFalse(row["z"]["permission"])

    def test_measure_root_records_live_counts(self):
        row = measure_root(
            ROOT,
            quoted_counts=[0, 0],
            keyword_counts=[3, 3],
        )
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(
            [item["state"] for item in row["quoted"]],
            ["FINDER-UNVERIFIED", "FINDER-UNVERIFIED"],
        )
        self.assertEqual(
            [item["state"] for item in row["keyword"]],
            ["SEARCH_HIT", "SEARCH_HIT"],
        )
        self.assertFalse(row["permission"])
        self.assertIn(CORNER_NAME, row["do_not_write"])

    def test_do_not_remint_includes_corner_and_readback(self):
        self.assertIn("cursor-claude-peer-check-corner-finder-20260902-01", DO_NOT_REMINT)
        self.assertIn(
            "cursor-claude-peer-check-corner-finder-readback-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn("cursor-claude-peer-check-seated-receive-20260902-01", DO_NOT_REMINT)
        self.assertTrue(DO_NOT_REWRITE)
        self.assertEqual(DO_NOT_WRITE, (CORNER_NAME,))
        self.assertIn(PEER_CHECK, SEARCH_SPACE)


if __name__ == "__main__":
    unittest.main()
