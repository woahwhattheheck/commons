#!/usr/bin/env python3
"""Wake-contract leftover: SPECTER rebase talk is not a land."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from wake_contract import (
    REQUIRED_PHRASES,
    SLACK_TS,
    SPECTER_JOB,
    SPECTER_REL,
    classify,
    measure_from_rows,
    measure_root,
)


class TestWakeContract(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_miss_is_finder_failed_never_zero(self):
        row = classify(
            {
                "measured": True,
                "calibration_ok": True,
                "search_space": ["host/wake_contract.py"],
            }
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("FINDER-FAILED", row["note"])
        self.assertIn("Never 0", row["note"])

    def test_complete_row_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "specter_job_present": True,
                "specter_owner": "SPECTER",
                "rivet_job_present": True,
                "rivet_status": "DONE",
                "tick_reopens": True,
                "last_tick_ignored": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "named_idle_bc_resume": "UNMEASURED",
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "INTEGRATED")

    def test_live_tree_has_the_leftover(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["specter_job_present"])
        self.assertEqual(row["specter_owner"], "SPECTER")
        self.assertTrue(row["rivet_job_present"])
        self.assertEqual(row["rivet_status"], "DONE")
        self.assertTrue(row["tick_reopens"])
        self.assertTrue(row["last_tick_ignored"])
        self.assertEqual(row["named_idle_bc_resume"], "UNMEASURED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787642890.990089")
        self.assertEqual(SPECTER_JOB, "specter-watchdog-head-proof-20260825-01")
        self.assertTrue(os.path.isfile(os.path.join(ROOT, SPECTER_REL)))
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
