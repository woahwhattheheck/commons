#!/usr/bin/env python3
"""Build-sweep leftover requires the emitter and refuses remints."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from build_sweep_act import (
    ALREADY_LANDED,
    CALIBRATION,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestBuildSweepAct(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify(
            {
                "measured": True,
                "calibration_ok": False,
                "calibration_hits": [],
                "card_present": True,
                "catalog_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])
        self.assertIn("never 0", verdict["note"].lower())

    def test_missing_emitter_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "emitter_present": False,
                "sweep_present": True,
                "misses": ["host/pixel_heartbeat_emit.py"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_missing_current_heartbeat_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "emitter_present": True,
                "sweep_present": True,
                "rivet_valid": False,
                "player2_preserved": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("PLAYER2", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "emitter_present": True,
                "sweep_present": True,
                "rivet_valid": True,
                "player2_preserved": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])
        self.assertIn("colony build", verdict["note"])

    def test_live_tree_measures_integrated(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertTrue(row["emitter_present"])
        self.assertTrue(row["rivet_valid"])
        self.assertTrue(row["player2_preserved"])
        self.assertEqual(verdict["state"], "INTEGRATED", verdict)
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertFalse(row["landed_missing"])
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)

    def test_catalog_names_first_action(self):
        catalog_path = os.path.join(ROOT, "ground", "BUILD_SWEEP_ACT.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        self.assertEqual(catalog["first_action"], "current pixel heartbeat emitter")
        self.assertIn("ground/OWNER_MACHINE_BUILD_SWEEP.md", catalog["already_landed"])

    def test_search_space_and_calibration_named(self):
        self.assertIn("ground/BUILD_SWEEP_ACT.md", SEARCH_SPACE)
        self.assertIn("host/pixel_heartbeat_emit.py", SEARCH_SPACE)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)
        self.assertIn("ground/OWNER_MACHINE_BUILD_SWEEP.md", ALREADY_LANDED)
        self.assertIn("ground/PIXEL_HEARTBEAT.md", ALREADY_LANDED)
        self.assertIn("ground/SITTING_REMINT.md", ALREADY_LANDED)


if __name__ == "__main__":
    unittest.main()
