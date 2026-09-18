#!/usr/bin/env python3
"""Terminal-catalog leftover measures; it does not remint SPECTER."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from terminal_catalog import (
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SPECTER_JOB,
    classify,
    measure_from_rows,
    measure_root,
)


class TestTerminalCatalog(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_missing_calibration_is_finder_unverified(self):
        row = classify({"measured": True, "calibration_ok": False})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("FINDER-UNVERIFIED", row["note"])
        self.assertIn("Never 0", row["note"])

    def test_stale_open_candidate_is_not_landed(self):
        row = classify(
            {
                "measured": True,
                "calibration_ok": True,
                "card_present": True,
                "catalog_present": True,
                "specter_job_present": True,
                "specter_status": "DONE",
                "rivet_job_present": True,
                "rivet_status": "DONE",
                "mcp_wake_state": "CANDIDATE",
                "mcp_wake_canary": "OPEN",
                "mcp_wake_card_open": True,
                "stranded_note_open": True,
                "stranded_card_empty": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "named_idle_bc_resume": "UNMEASURED",
                "no_auth": True,
                "no_gate": True,
                "search_space": list(SEARCH_SPACE),
            }
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("FINDER-FAILED", row["note"])
        self.assertIn("OPEN/CANDIDATE", row["note"])

    def test_reconciled_catalog_is_integrated(self):
        row = classify(
            {
                "measured": True,
                "calibration_ok": True,
                "card_present": True,
                "catalog_present": True,
                "specter_job_present": True,
                "specter_status": "DONE",
                "rivet_job_present": True,
                "rivet_status": "DONE",
                "mcp_wake_state": "VERIFIED",
                "mcp_wake_canary": "DONE",
                "mcp_wake_card_open": False,
                "stranded_wake": "VERIFIED",
                "stranded_note_open": False,
                "stranded_card_empty": False,
                "found_phrases": list(REQUIRED_PHRASES),
                "named_idle_bc_resume": "UNMEASURED",
                "no_auth": True,
                "no_gate": True,
                "search_space": list(SEARCH_SPACE),
            }
        )
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertIn("still not the file", row["note"])

    def test_measure_from_rows_keeps_named_idle_unmeasured(self):
        row = measure_from_rows({"named_idle_bc_resume": "UNMEASURED"})
        self.assertTrue(row["measured"])
        self.assertEqual(row["named_idle_bc_resume"], "UNMEASURED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")

    def test_live_tree_matches_done_jobs(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["specter_status"], "DONE")
        self.assertEqual(row["rivet_status"], "DONE")
        self.assertEqual(row["mcp_wake_state"], "VERIFIED")
        self.assertEqual(row["mcp_wake_canary"], "DONE")
        self.assertFalse(row["mcp_wake_card_open"])
        self.assertEqual(row["stranded_wake"], "VERIFIED")
        self.assertFalse(row["stranded_note_open"])
        self.assertFalse(row["stranded_card_empty"])
        self.assertEqual(row["named_idle_bc_resume"], "UNMEASURED")
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertEqual(SPECTER_JOB, "specter-watchdog-head-proof-20260825-01")


if __name__ == "__main__":
    unittest.main()
