#!/usr/bin/env python3
"""Human-outcomes leftover names four jobs and stores no payout data."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from human_outcomes import (
    CALIBRATION,
    REQUIRED_GATE_OPEN,
    REQUIRED_OFFER_IDS,
    REQUIRED_PRICES,
    SEARCH_SPACE,
    SLACK_TS,
    TAKING_PATH,
    classify,
    load_pack,
    measure_from_rows,
    measure_root,
)


class TestHumanOutcomes(unittest.TestCase):
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
                "pack_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("Instrument failure", verdict["note"])
        self.assertEqual(verdict["z"], "FINDER-FAILED")

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "pack_present": False,
                "misses": ["ground/HUMAN_OUTCOMES.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertEqual(classify(measured)["z"], "FINDER-FAILED")

    def test_claimed_cash_is_not_landed(self):
        catalog_path = os.path.join(ROOT, "revenue", "human_outcomes", "offers.json")
        with open(catalog_path, encoding="utf-8") as handle:
            pack = load_pack(handle.read())
        measured = measure_from_rows(
            {
                "card_present": True,
                "pack_present": True,
                "kind": pack["kind"],
                "mandate": pack["mandate"],
                "demand": "UNKNOWN",
                "gate_pack": "READY",
                "gate_owner": "NEEDS_OWNER_PRIVATE",
                "gate_buyer": "NEEDS_BUYER",
                "gate_cash": "NOT_LANDED",
                "gate_cash_usd": 0,
                "gate_open": list(REQUIRED_GATE_OPEN),
                "ready_does_not_mean_cash": True,
                "collectable_usd": "NOT_LANDED",
                "collected_cash_usd": 12,
                "banking_only_blocker": False,
                "computer_is_the_product": False,
                "overwrites_commercial_json": False,
                "overwrites_dio": False,
                "overwrites_payment_ready": False,
                "overwrites_portfolio_overdrive": False,
                "overwrites_subzero_buyers": False,
                "overwrites_subzero_gtm": False,
                "no_checkout": True,
                "no_auth": True,
                "no_gate": True,
                "no_buyer_fiction": True,
                "founder_sent_contact": True,
                "human_value_not_proof_worship": True,
                "does_not_replace": [
                    "white-box-gguf-pilot-30d",
                    "gguf-diagnostic-10d-12k",
                ],
                "fulfillment_modules_remain": ["SUBZERO", "compression", "DIO"],
                "offer_ids": list(REQUIRED_OFFER_IDS),
                "offer_prices": dict(REQUIRED_PRICES),
                "white_box_offer_id": "white-box-gguf-pilot-30d",
                "commercial_offer_id": "white-box-gguf-pilot-30d",
                "white_box_fee": 30000,
                "payment_offer_id": "gguf-diagnostic-10d-12k",
                "payment_fee": 12000,
                "dio_present": True,
                "door_present": True,
                "fulfillment_present": True,
                "taking_state": "CARRIER_ONLY",
                "xyz_required": True,
                "remeasurement_owner": "Codex / Grok Build",
                "titan": "NOT_WRITTEN",
                "payment_collection": "NOT_PROVIDED_ON_THIS_PAGE",
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
        self.assertEqual(row["collected_cash_usd"], 0)
        self.assertEqual(row["white_box_fee"], 30000)
        self.assertEqual(row["payment_fee"], 12000)
        self.assertTrue(row["no_checkout"])
        self.assertTrue(row["no_buyer_fiction"])
        self.assertEqual(row["taking_state"], "CARRIER_ONLY")
        self.assertFalse(os.path.isfile(os.path.join(ROOT, TAKING_PATH)))
        self.assertIn("white-box-gguf-pilot-30d", row["does_not_replace"])
        self.assertIn("gguf-diagnostic-10d-12k", row["does_not_replace"])
        for offer_id in REQUIRED_OFFER_IDS:
            self.assertIn(offer_id, row["offer_ids"])
            self.assertEqual(row["offer_prices"][offer_id], REQUIRED_PRICES[offer_id])
        for rel in CALIBRATION:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)
        self.assertEqual(row["slack_ts"], SLACK_TS)
        for rel in SEARCH_SPACE:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)
        door = os.path.join(ROOT, "humans.html")
        with open(door, encoding="utf-8") as handle:
            html = handle.read()
        self.assertIn("HUMAN OUTCOMES INTEREST", html)
        self.assertIn("no checkout", html.lower())


if __name__ == "__main__":
    unittest.main()
