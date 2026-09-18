#!/usr/bin/env python3
"""A11 leftover: named --go refuse. Never silent 0. Never fires."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_go_refuse import (
    CALIBRATION,
    CORNER_NAME,
    DO_NOT_REMINT,
    DO_NOT_REWRITE,
    DO_NOT_SMASH,
    DO_NOT_WRITE,
    PEER_CHECK,
    SEARCH_SPACE,
    classify,
    go_row,
    measure_from_rows,
    measure_root,
    self_test,
)


def _complete(**overrides):
    facts = {
        "calibration_ok": True,
        "calibration_hits": list(CALIBRATION),
        "no_auth": True,
        "no_gate": True,
        "posting": "OPEN",
        "go": go_row(True, "FINDER-FAILED"),
        "wrote_corner": False,
        "smashed_mno": False,
        "treated_found_as_go": False,
        "treated_hit_as_go": False,
        "treated_refuse_as_fire": False,
    }
    facts.update(overrides)
    return measure_from_rows(facts)


class TestClaudeGoRefuse(unittest.TestCase):
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

    def test_unasked_is_not_a_fire(self):
        row = go_row(False, "FINDER-FAILED")
        self.assertEqual(row["state"], "UNASKED")
        self.assertFalse(row["asked"])
        self.assertFalse(row["fired"])
        self.assertFalse(row["permission"])
        self.assertIn("not a fire", row["note"])

    def test_go_is_refused_and_never_fires(self):
        row = go_row(True, "FINDER-FAILED")
        self.assertEqual(row["state"], "REFUSED")
        self.assertTrue(row["asked"])
        self.assertFalse(row["fired"])
        self.assertFalse(row["permission"])
        self.assertIn("never silent 0", row["note"])

    def test_found_is_not_go(self):
        row = go_row(True, "FOUND")
        self.assertEqual(row["state"], "REFUSED")
        self.assertEqual(row["laptop"], "FOUND")
        self.assertFalse(row["permission"])
        self.assertIn("FOUND is not --go", row["note"])

    def test_hit_is_not_graduation(self):
        row = go_row(True, "HIT")
        self.assertEqual(row["state"], "REFUSED")
        self.assertEqual(row["laptop"], "HIT")
        self.assertIn("not graduation", row["note"])

    def test_found_treated_as_go_is_refused(self):
        row = classify(_complete(go=go_row(True, "FOUND"), treated_found_as_go=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("FOUND treated as --go", row["note"])

    def test_hit_treated_as_go_is_refused(self):
        row = classify(_complete(go=go_row(True, "HIT"), treated_hit_as_go=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("HIT treated as --go", row["note"])

    def test_refuse_treated_as_fire_is_refused(self):
        row = classify(_complete(treated_refuse_as_fire=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("not actuation", row["note"])

    def test_smashed_mno_is_refused(self):
        row = classify(_complete(smashed_mno=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("commons.mno", row["note"])

    def test_this_seat_recorded_sample_is_integrated(self):
        row = classify(_complete())
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["z"]["go"], "REFUSED")
        self.assertFalse(row["z"]["fired"])
        self.assertFalse(row["z"]["permission"])

    def test_measure_root_records_live_refuse(self):
        row = measure_root(ROOT, asked=True, laptop_state="FINDER-FAILED")
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["go"]["state"], "REFUSED")
        self.assertFalse(row["go"]["fired"])
        self.assertFalse(row["permission"])
        self.assertIn(CORNER_NAME, row["do_not_write"])
        self.assertFalse(os.path.isfile(os.path.join(ROOT, CORNER_NAME)))

    def test_do_not_remint_includes_laptop_and_speaker(self):
        self.assertIn(
            "cursor-claude-peer-check-laptop-finder-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn(
            "cursor-claude-peer-check-laptop-finder-readback-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn(
            "cursor-claude-peer-check-seated-builder-speaker-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn(
            "cursor-claude-peer-check-seated-builder-speaker-readback-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn("cursor-claude-peer-check-seated-receive-20260902-01", DO_NOT_REMINT)
        self.assertTrue(DO_NOT_REWRITE)
        self.assertEqual(DO_NOT_WRITE, (CORNER_NAME,))
        self.assertEqual(DO_NOT_SMASH, ("commons.mno",))
        self.assertIn(PEER_CHECK, SEARCH_SPACE)
        self.assertIn("--go", SEARCH_SPACE)


if __name__ == "__main__":
    unittest.main()
