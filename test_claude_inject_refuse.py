#!/usr/bin/env python3
"""A11 leftover: named --inject 0x01 refuse. Never silent 0. Never writes."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_inject_refuse import (
    CALIBRATION,
    CORNER_NAME,
    DO_NOT_INJECT,
    DO_NOT_REMINT,
    DO_NOT_REWRITE,
    DO_NOT_SMASH,
    DO_NOT_WRITE,
    INJECT_FILL,
    PEER_CHECK,
    SEARCH_SPACE,
    classify,
    inject_row,
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
        "inject": inject_row(True, INJECT_FILL),
        "wrote_corner": False,
        "smashed_mno": False,
        "injected_fill": False,
        "treated_refuse_as_inject": False,
        "treated_inject_as_fill": False,
        "treated_inject_as_go": False,
        "fired_go": False,
    }
    facts.update(overrides)
    return measure_from_rows(facts)


class TestClaudeInjectRefuse(unittest.TestCase):
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

    def test_unasked_is_not_an_inject(self):
        row = inject_row(False, INJECT_FILL)
        self.assertEqual(row["state"], "UNASKED")
        self.assertFalse(row["asked"])
        self.assertFalse(row["injected"])
        self.assertFalse(row["wiped"])
        self.assertFalse(row["permission"])
        self.assertIn("not an inject", row["note"])

    def test_inject_is_refused_and_never_writes(self):
        row = inject_row(True, INJECT_FILL)
        self.assertEqual(row["state"], "REFUSED")
        self.assertTrue(row["asked"])
        self.assertFalse(row["injected"])
        self.assertFalse(row["wiped"])
        self.assertFalse(row["wrote"])
        self.assertFalse(row["permission"])
        self.assertIn("never silent 0", row["note"])
        self.assertIn("new=old|mask", row["note"])

    def test_unknown_fill_is_finder_failed(self):
        row = inject_row(True, "0x02")
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertEqual(row["fill"], "0x02")
        self.assertFalse(row["injected"])
        self.assertIn("never silent 0", row["note"])

    def test_refuse_treated_as_inject_is_refused(self):
        row = classify(_complete(treated_refuse_as_inject=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("not a write", row["note"])

    def test_inject_treated_as_fill_is_refused(self):
        row = classify(_complete(treated_inject_as_fill=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("new=old|mask", row["note"])

    def test_inject_treated_as_go_is_refused(self):
        row = classify(_complete(treated_inject_as_go=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("Inject is not --go", row["note"])

    def test_fired_go_is_refused(self):
        row = classify(_complete(fired_go=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("fired --go", row["note"])

    def test_injected_fill_is_refused(self):
        row = classify(_complete(injected_fill=True))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("wipe", row["note"])

    def test_this_seat_recorded_sample_is_integrated(self):
        row = classify(_complete())
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["z"]["inject"], "REFUSED")
        self.assertFalse(row["z"]["injected"])
        self.assertFalse(row["z"]["wiped"])
        self.assertFalse(row["z"]["permission"])

    def test_measure_root_records_live_refuse(self):
        row = measure_root(ROOT, asked=True, fill=INJECT_FILL)
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["inject"]["state"], "REFUSED")
        self.assertFalse(row["inject"]["injected"])
        self.assertFalse(row["inject"]["wiped"])
        self.assertFalse(row["permission"])
        self.assertIn(CORNER_NAME, row["do_not_write"])
        self.assertIn(INJECT_FILL, row["do_not_inject"])
        self.assertFalse(os.path.isfile(os.path.join(ROOT, CORNER_NAME)))

    def test_do_not_remint_includes_smash_refuse(self):
        self.assertIn(
            "cursor-claude-peer-check-smash-refuse-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn(
            "cursor-claude-peer-check-smash-refuse-readback-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn(
            "cursor-claude-peer-check-corner-write-refuse-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn(
            "cursor-claude-peer-check-go-refuse-20260902-01",
            DO_NOT_REMINT,
        )
        self.assertIn("cursor-claude-peer-check-seated-receive-20260902-01", DO_NOT_REMINT)
        self.assertTrue(DO_NOT_REWRITE)
        self.assertEqual(DO_NOT_WRITE, (CORNER_NAME,))
        self.assertEqual(DO_NOT_SMASH, ("commons.mno",))
        self.assertEqual(DO_NOT_INJECT, (INJECT_FILL,))
        self.assertIn(PEER_CHECK, SEARCH_SPACE)
        self.assertIn("--inject", SEARCH_SPACE)
        self.assertIn("inject 0x01 as fill", SEARCH_SPACE)


if __name__ == "__main__":
    unittest.main()
