#!/usr/bin/env python3
"""A11 leftover: named CLAUDE_CORNER.md walk. Never silent 0."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_corner_finder import (
    CALIBRATION,
    CORNER_NAME,
    DO_NOT_REMINT,
    DO_NOT_REWRITE,
    DO_NOT_WRITE,
    SEARCH_SPACE,
    WALK_DIRS,
    classify,
    laptop_row,
    measure_from_rows,
    measure_root,
    self_test,
    slack_search_census,
    walk_row,
)


def _complete(**overrides):
    facts = {
        "calibration_ok": True,
        "calibration_hits": list(CALIBRATION),
        "no_auth": True,
        "no_gate": True,
        "posting": "OPEN",
        "walk": [{"path": CORNER_NAME, "state": "FINDER-FAILED"}],
        "slack": slack_search_census(0),
        "laptop": {"state": "FINDER-FAILED"},
        "wrote_corner": False,
    }
    facts.update(overrides)
    return measure_from_rows(facts)


class TestClaudeCornerFinder(unittest.TestCase):
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

    def test_empty_slack_search_is_finder_unverified_not_clear(self):
        row = slack_search_census(0)
        self.assertEqual(row["state"], "FINDER-UNVERIFIED")
        self.assertEqual(row["count"], 0)
        self.assertIn("never silent 0", row["note"])
        classified = classify(_complete(slack={"state": "CLEAR", "count": 0}))
        self.assertEqual(classified["state"], "NOT_LANDED")
        self.assertIn("CZ-03", classified["note"])

    def test_walk_missing_is_finder_failed(self):
        with tempfile.TemporaryDirectory(prefix="corner-miss-") as tmp:
            row = walk_row(tmp, ".")
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertIsNone(row["count"])
        self.assertFalse(row["present"])

    def test_walk_present_is_hit_not_graduation(self):
        with tempfile.TemporaryDirectory(prefix="corner-hit-") as tmp:
            with open(os.path.join(tmp, CORNER_NAME), "w", encoding="utf-8") as handle:
                handle.write("architect close-the-case\n")
            row = walk_row(tmp, ".")
        self.assertEqual(row["state"], "HIT")
        self.assertEqual(row["count"], 1)
        self.assertTrue(row["present"])

    def test_fixture_absent_is_integrated(self):
        with tempfile.TemporaryDirectory(prefix="corner-live-") as tmp:
            os.makedirs(os.path.join(tmp, "ground"))
            os.makedirs(os.path.join(tmp, "muhl", "docs"))
            os.makedirs(os.path.join(tmp, "ground", "pc-purge-20260820"))
            os.makedirs(os.path.join(tmp, "evidence", "bully_sessions"))
            os.makedirs(os.path.join(tmp, "host"))
            with open(os.path.join(tmp, "ground", "HEAD.md"), "w", encoding="utf-8") as handle:
                handle.write("HEAD truth\n")
            with open(
                os.path.join(tmp, "ground", "CLAUDE_PEER_CHECK.md"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("A11 HIT-SR01 CLAUDE_CORNER.md write = failure\n")
            with open(
                os.path.join(tmp, "host", "claude_corner_finder.py"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("# leftover\n")
            row = measure_root(tmp, slack_count=0)
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertTrue(row["calibration_ok"])
        self.assertIs(row["permission"], False)
        self.assertEqual(row["posting"], "OPEN")
        self.assertEqual([item["state"] for item in row["walk"]], ["FINDER-FAILED"] * 5)
        self.assertEqual(row["slack"]["state"], "FINDER-UNVERIFIED")
        self.assertIn(CORNER_NAME, DO_NOT_WRITE)

    def test_live_tree_measures_finder_failed_without_writing(self):
        row = measure_root(ROOT, slack_count=0)
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["posting"], "OPEN")
        self.assertTrue(row["no_auth"])
        self.assertTrue(row["no_gate"])
        self.assertIs(row["permission"], False)
        self.assertEqual(len(WALK_DIRS), 5)
        self.assertEqual([item["state"] for item in row["walk"]], ["FINDER-FAILED"] * 5)
        self.assertTrue(all(item["count"] is None for item in row["walk"]))
        self.assertEqual(row["z"]["corner"], "FINDER-FAILED")
        self.assertEqual(row["slack"]["state"], "FINDER-UNVERIFIED")
        self.assertEqual(row["laptop"]["state"], "FINDER-FAILED")
        self.assertIn("cursor-claude-peer-check-seated-receive-20260902-01", DO_NOT_REMINT)
        self.assertIn(
            "cursor-claude-peer-check-sr01-soft-dumps-readback-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertEqual(len(DO_NOT_REWRITE), 6)
        self.assertFalse(os.path.isfile(os.path.join(ROOT, CORNER_NAME)))
        self.assertIn(os.path.join("muhl", "docs", CORNER_NAME), SEARCH_SPACE)
        laptop = laptop_row()
        self.assertEqual(laptop["state"], "FINDER-FAILED")
        self.assertIsNone(laptop["count"])


if __name__ == "__main__":
    unittest.main()
