#!/usr/bin/env python3
"""SUBZERO GTM leftover names additive SKUs and stores no payout data."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from subzero_gtm import (
    CALIBRATION,
    REQUIRED_GATE_OPEN,
    REQUIRED_HORIZONS,
    REQUIRED_PATH_IDS,
    SEARCH_SPACE,
    SLACK_TS,
    TAKING_PATH,
    classify,
    first_validation_price,
    load_arch,
    measure_from_rows,
    measure_root,
)


class TestSubzeroGtm(unittest.TestCase):
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
                "arch_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("Instrument failure", verdict["note"])
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "arch_present": False,
                "misses": ["ground/SUBZERO_GTM.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertEqual(classify(measured)["z"], "FINDER-FAILED")

    def test_claimed_cash_is_not_landed(self):
        catalog_path = os.path.join(ROOT, "revenue", "subzero_gtm", "architecture.json")
        with open(catalog_path, encoding="utf-8") as handle:
            arch = load_arch(handle.read())
        measured = measure_from_rows(
            {
                "card_present": True,
                "arch_present": True,
                "kind": arch["kind"],
                "mandate": arch["mandate"],
                "panel": arch["panel"],
                "first_price": 2500,
                "demand": "UNKNOWN",
                "runtime_intelligence_claimed": False,
                "runtime_status": "UNMEASURED_ON_THIS_TREE",
                "demand_status": "UNKNOWN",
                "structural_status": "MEASURED_ON_PUBLIC_TREE",
                "gate_pack": "READY",
                "gate_owner": "NEEDS_OWNER_PRIVATE",
                "gate_buyer": "NEEDS_BUYER",
                "gate_cash": "NOT_LANDED",
                "gate_cash_usd": 0,
                "gate_open": list(REQUIRED_GATE_OPEN),
                "ready_does_not_mean_cash": True,
                "collectable_usd": "NOT_LANDED",
                "collected_cash_usd": 1,
                "banking_only_blocker": False,
                "computer_is_the_product": False,
                "overwrites_commercial_json": False,
                "overwrites_dio": False,
                "overwrites_payment_ready": False,
                "overwrites_portfolio_overdrive": False,
                "overwrites_subzero_buyers": False,
                "implements_p01": "P01_catalog_receipt",
                "buyers_present": True,
                "does_not_replace": [
                    "white-box-gguf-pilot-30d",
                    "gguf-diagnostic-10d-12k",
                ],
                "path_ids": list(REQUIRED_PATH_IDS),
                "horizon_keys": list(REQUIRED_HORIZONS),
                "commercial_offer_id": "white-box-gguf-pilot-30d",
                "white_box_fee": 30000,
                "payment_offer_id": "gguf-diagnostic-10d-12k",
                "payment_fee": 12000,
                "portfolio_now_active": "high-ticket-white-box",
                "portfolio_collectable": "NOT_LANDED",
                "dio_present": True,
                "excerpts_present": True,
                "taking_state": "CARRIER_ONLY",
                "xyz_required": True,
                "remeasurement_owner": "Cursor / Grok",
                "titan": "NOT_WRITTEN",
                "subzero_now_active": "none",
                "dissent_present": True,
                "product_is_not": "not intelligence",
                "forbidden_hits": [],
                "calibration_ok": True,
                "misses": [],
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertEqual(classify(measured)["z"], "FINDER-FAILED")

    def test_live_tree_is_integrated_and_does_not_remint(self):
        row = measure_root(ROOT)
        verdict = classify(row)
        self.assertEqual(verdict["state"], "INTEGRATED", verdict)
        self.assertEqual(row["first_price"], 2500)
        self.assertEqual(row["white_box_fee"], 30000)
        self.assertEqual(row["payment_fee"], 12000)
        self.assertEqual(row["collected_cash_usd"], 0)
        self.assertFalse(row["runtime_intelligence_claimed"])
        self.assertEqual(row["taking_state"], "CARRIER_ONLY")
        self.assertFalse(os.path.isfile(os.path.join(ROOT, TAKING_PATH)))
        self.assertIn("white-box-gguf-pilot-30d", row["does_not_replace"])
        self.assertIn("gguf-diagnostic-10d-12k", row["does_not_replace"])
        self.assertEqual(row["implements_p01"], "P01_catalog_receipt")
        self.assertTrue(row["buyers_present"])
        self.assertFalse(row["overwrites_subzero_buyers"])
        for horizon in REQUIRED_HORIZONS:
            self.assertIn(horizon, row["horizon_keys"])
        for path_id in REQUIRED_PATH_IDS:
            self.assertIn(path_id, row["path_ids"])
        for rel in CALIBRATION:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)
        self.assertEqual(row["slack_ts"], SLACK_TS)
        catalog_path = os.path.join(ROOT, "revenue", "subzero_gtm", "architecture.json")
        with open(catalog_path, encoding="utf-8") as handle:
            arch = load_arch(handle.read())
        self.assertEqual(first_validation_price(arch), 2500)
        self.assertGreaterEqual(len(arch["path_ids"]), 12)
        for rel in SEARCH_SPACE:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)


if __name__ == "__main__":
    unittest.main()
