#!/usr/bin/env python3
"""Live-Titan test quarantine leftover names isolation and refuses remint."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from titan_test_quarantine import (
    CALIBRATION,
    FORBIDDEN_PHRASES,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SLACK_TS,
    classify,
    load_catalog,
    measure_from_rows,
    measure_root,
)


class TestTitanTestQuarantine(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertIn("never 0", row["note"].lower())

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

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/TITAN_TEST_QUARANTINE.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_live_actuation_test_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "forbidden_hits": list(FORBIDDEN_PHRASES),
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "apply_off": True,
                "refuse_mutate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("live-owner", verdict["note"])

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "forbidden_hits": [],
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "apply_off": True,
                "refuse_mutate": True,
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_measures_integrated(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertFalse(row["forbidden_hits"])
        self.assertEqual(row.get("slack_ts") or SLACK_TS, SLACK_TS)

    def test_catalog_and_search_space(self):
        catalog_path = os.path.join(ROOT, "ground", "TITAN_TEST_QUARANTINE.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["posting"], "OPEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        self.assertFalse(catalog["apply"])
        self.assertIn("ground/TITAN_TEST_QUARANTINE.md", SEARCH_SPACE)
        self.assertIn("host/titan_move_offsets.py", SEARCH_SPACE)
        self.assertIn("ground/EXECUTE.md", CALIBRATION)
        self.assertIn("ground/TITAN_APPEND_GUARD.md", CALIBRATION)


if __name__ == "__main__":
    unittest.main()
