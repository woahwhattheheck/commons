#!/usr/bin/env python3
"""55_portfolio_overdrive leftover ranks ten lanes and stores no payout data."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from portfolio_overdrive import (
    CALIBRATION,
    REQUIRED_HORIZONS,
    REQUIRED_LANES,
    SEARCH_SPACE,
    SLACK_TS,
    TAKING_PATH,
    classify,
    lane_gaps,
    load_catalog,
    measure_bazaar,
    measure_from_rows,
    measure_root,
)


class TestPortfolioOverdrive(unittest.TestCase):
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
                "card_present": True,
                "catalog_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("Instrument failure", verdict["note"])
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/PORTFOLIO_OVERDRIVE.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertEqual(classify(measured)["z"], "FINDER-FAILED")

    def test_erased_lane_is_not_landed(self):
        catalog_path = os.path.join(ROOT, "revenue", "portfolio_overdrive", "portfolio.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        lanes = list(catalog["lanes"])
        lanes[0] = dict(lanes[0], erased=True)
        gaps = lane_gaps(lanes)
        self.assertEqual(gaps["erased"], ["high-ticket-white-box"])
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "mandate": "55_portfolio_overdrive",
                "horizons": list(REQUIRED_HORIZONS),
                "lane_gaps": gaps,
                "rank_but_do_not_erase": True,
                "computer_is_the_product": False,
                "collectable_usd": "NOT_LANDED",
                "banking_only_blocker": False,
                "usd_offer_count": 0,
                "bazaar_currency": "FREE_COLONY_COMPUTE",
                "white_box_fee": 30000,
                "dio_present": True,
                "taking_state": "CARRIER_ONLY",
                "xyz_required": True,
                "remeasurement_owner": "Codex / Grok Build",
                "titan": "NOT_WRITTEN",
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "revenue", "portfolio_overdrive", "portfolio.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["mandate"], "55_portfolio_overdrive")
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(catalog["taking_state"], "CARRIER_ONLY")
        self.assertEqual(catalog["collectable_usd"], "NOT_LANDED")
        self.assertFalse(catalog["banking_only_blocker"])
        self.assertTrue(catalog["rank_but_do_not_erase"])
        self.assertFalse(catalog["computer_is_the_product"])
        self.assertEqual(catalog["horizons"], list(REQUIRED_HORIZONS))
        self.assertEqual(catalog["required_lanes"], list(REQUIRED_LANES))
        gaps = lane_gaps(catalog["lanes"])
        self.assertEqual(gaps["missing_ids"], [])
        self.assertEqual(gaps["erased"], [])
        self.assertEqual(gaps["field_miss"], [])
        self.assertEqual(gaps["horizon_miss"], [])
        self.assertTrue(gaps["rank_ok"])
        self.assertEqual(gaps["ids"], list(REQUIRED_LANES))
        bazaar_path = os.path.join(ROOT, "bazaar.json")
        with open(bazaar_path, encoding="utf-8") as handle:
            bazaar = measure_bazaar(handle.read())
        self.assertEqual(bazaar["usd_offer_count"], 0)
        self.assertEqual(bazaar["currency"], "FREE_COLONY_COMPUTE")
        row = measure_root(ROOT)
        self.assertTrue(row["calibration_ok"], "known-present calibration must hit EXECUTE + Action Pad")
        self.assertEqual(sorted(row["calibration_hits"]), sorted(CALIBRATION))
        self.assertEqual(row["search_space"], list(SEARCH_SPACE))
        self.assertEqual(row["taking_state"], "CARRIER_ONLY")
        self.assertFalse(row["taking_present"])
        self.assertEqual(row["usd_offer_count"], 0)
        self.assertEqual(row["white_box_fee"], 30000)
        self.assertTrue(row["dio_present"])
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertFalse(os.path.isfile(os.path.join(ROOT, TAKING_PATH)))
        self.assertTrue(os.path.isdir(os.path.join(ROOT, "revenue", "dio")))


if __name__ == "__main__":
    unittest.main()
