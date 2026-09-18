#!/usr/bin/env python3
"""Cash-now leftover names three stages; it does not store payout data."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from cash_now import (
    CALIBRATION,
    REQUIRED_PHRASES,
    REQUIRED_STAGES,
    SEARCH_SPACE,
    SLACK_TS,
    TAKING_PATH,
    classify,
    load_catalog,
    measure_bazaar,
    measure_from_rows,
    measure_root,
)


class TestCashNow(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])
        self.assertEqual(row["z"], "FINDER-FAILED")

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
        self.assertIn("Instrument failure", verdict["note"])
        self.assertIn("Never 0", verdict["note"])
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/CASH_NOW.md"],
                "calibration_ok": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_usd_offer_is_not_enough_without_stages(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "stages": ["AUTHORIZATION"],
                "needs_bryce": {
                    "need": "payout destination",
                    "why_only_bryce": "owner UI only",
                    "smallest_action": "connect destination privately",
                    "evidence": "CASH_NOW.json",
                    "after": "list a USD offer",
                },
                "usd_offer_count": 0,
                "bazaar_currency": "FREE_COLONY_COMPUTE",
                "taking_state": "CARRIER_ONLY",
                "banking_only_blocker": False,
                "collectable_usd": "NOT_LANDED",
                "xyz_required": True,
                "remeasurement_owner": "Codex / Grok Build",
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "found_phrases": list(REQUIRED_PHRASES),
                "stages": list(REQUIRED_STAGES),
                "needs_bryce": {
                    "need": "payout destination",
                    "why_only_bryce": "owner UI only",
                    "smallest_action": "connect destination privately",
                    "evidence": "CASH_NOW.json",
                    "after": "list a USD offer",
                },
                "usd_offer_count": 0,
                "bazaar_currency": "FREE_COLONY_COMPUTE",
                "taking_state": "CARRIER_ONLY",
                "banking_only_blocker": False,
                "collectable_usd": "NOT_LANDED",
                "xyz_required": True,
                "remeasurement_owner": "Codex / Grok Build",
                "forbidden_hits": [],
                "calibration_ok": True,
                "calibration_hits": list(CALIBRATION),
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "CASH_NOW.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(catalog["taking_state"], "CARRIER_ONLY")
        self.assertEqual(catalog["collectable_usd"], "NOT_LANDED")
        self.assertFalse(catalog["banking_only_blocker"])
        self.assertTrue(catalog["xyz_required"])
        self.assertEqual(catalog["remeasurement_owner"], "Codex / Grok Build")
        self.assertEqual(catalog["stages"], list(REQUIRED_STAGES))
        self.assertGreaterEqual(len(catalog["rails"]), 2)
        self.assertTrue(catalog["needs_bryce"]["smallest_action"])
        bazaar_path = os.path.join(ROOT, "bazaar.json")
        with open(bazaar_path, encoding="utf-8") as handle:
            bazaar = measure_bazaar(handle.read())
        self.assertEqual(bazaar["usd_offer_count"], 0)
        self.assertEqual(bazaar["currency"], "FREE_COLONY_COMPUTE")
        self.assertGreaterEqual(bazaar["offer_count"], 1)
        row = measure_root(ROOT)
        self.assertTrue(row["calibration_ok"], "known-present calibration must hit EXECUTE + Action Pad")
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertEqual(row["search_space"], list(SEARCH_SPACE))
        self.assertEqual(row["taking_state"], "DURABLE_ON_MAIN")
        self.assertTrue(row["taking_present"])
        self.assertTrue(row["taking_provenance_ok"])
        self.assertEqual(row["taking_provenance_mismatches"], [])
        hostile = dict(row, taking_state="UNVERIFIED_PRESENT", taking_provenance_ok=False)
        self.assertEqual(classify(hostile)["state"], "NOT_LANDED")
        self.assertEqual(row["usd_offer_count"], 0)
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("authorization", row["found_phrases"])
        self.assertIn("settlement", row["found_phrases"])
        self.assertTrue(os.path.isfile(os.path.join(ROOT, TAKING_PATH)))


if __name__ == "__main__":
    unittest.main()
