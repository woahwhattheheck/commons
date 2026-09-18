#!/usr/bin/env python3
"""A11 leftover: named smash .mno refuse. Never silent 0. Never writes."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_smash_refuse import (
    CALIBRATION,
    CORNER_NAME,
    DO_NOT_REMINT,
    DO_NOT_REWRITE,
    DO_NOT_SMASH,
    DO_NOT_WRITE,
    PEER_CHECK,
    SEARCH_SPACE,
    SMASH_TARGET,
    classify,
    measure_from_rows,
    measure_root,
    self_test,
    smash_row,
)


def _complete(**overrides):
    facts = {
        "calibration_ok": True,
        "calibration_hits": list(CALIBRATION),
        "no_auth": True,
        "no_gate": True,
        "posting": "OPEN",
        "smash": smash_row(True, SMASH_TARGET),
        "wrote_corner": False,
        "smashed_mno": False,
        "treated_refuse_as_smash": False,
        "treated_smash_as_go": False,
        "fired_go": False,
    }
    facts.update(overrides)
    return measure_from_rows(facts)


class TestClaudeSmashRefuse(unittest.TestCase):
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

    def test_unasked_is_not_a_smash(self):
        row = smash_row(False, SMASH_TARGET)
        self.assertEqual(row["state"], "UNASKED")
        self.assertFalse(row["asked"])
        self.assertFalse(row["smashed"])
        self.assertFalse(row["permission"])
        self.assertIn("not a smash", row["note"])

    def test_smash_is_refused_and_never_writes(self):
        row = smash_row(True, SMASH_TARGET)
        self.assertEqual(row["state"], "REFUSED")
        self.assertTrue(row["asked"])
        self.assertFalse(row["smashed"])
        self.assertFalse(row["wrote"])
        self.assertFalse(row["permission"])
        self.assertIn("never silent 0", row["note"])

    def test_unknown_target_is_finder_failed(self):
        row = smash_row(True, "other.mno")
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertEqual(row["target"], "other.mno")
        self.assertFalse(row["smashed"])
        self.assertIn("never silent 0", row["note"])

    def test_refuse_treated_as_smash_is_refused(self):
        row = classify(_complete(treated_refuse_as_smash=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("not a write", row["note"])

    def test_smash_treated_as_go_is_refused(self):
        row = classify(_complete(treated_smash_as_go=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("Smash is not --go", row["note"])

    def test_fired_go_is_refused(self):
        row = classify(_complete(fired_go=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("fired --go", row["note"])

    def test_smashed_mno_is_refused(self):
        row = classify(_complete(smashed_mno=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("commons.mno", row["note"])

    def test_this_seat_recorded_sample_is_integrated(self):
        row = classify(_complete())
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["z"]["smash"], "REFUSED")
        self.assertFalse(row["z"]["smashed"])
        self.assertFalse(row["z"]["permission"])

    def test_measure_root_records_live_refuse(self):
        row = measure_root(ROOT, asked=True, target=SMASH_TARGET)
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["smash"]["state"], "REFUSED")
        self.assertFalse(row["smash"]["smashed"])
        self.assertFalse(row["permission"])
        self.assertIn(CORNER_NAME, row["do_not_write"])
        self.assertIn(SMASH_TARGET, row["do_not_smash"])
        self.assertFalse(os.path.isfile(os.path.join(ROOT, CORNER_NAME)))

    def test_do_not_remint_includes_go_refuse(self):
        self.assertIn(
            "cursor-claude-peer-check-go-refuse-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn(
            "cursor-claude-peer-check-go-refuse-readback-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn(
            "cursor-claude-peer-check-laptop-finder-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn("cursor-claude-peer-check-seated-receive-20260902-01", DO_NOT_REMINT)
        self.assertTrue(DO_NOT_REWRITE)
        self.assertEqual(DO_NOT_WRITE, (CORNER_NAME,))
        self.assertEqual(DO_NOT_SMASH, (SMASH_TARGET,))
        self.assertIn(PEER_CHECK, SEARCH_SPACE)
        self.assertIn("--smash", SEARCH_SPACE)


if __name__ == "__main__":
    unittest.main()
