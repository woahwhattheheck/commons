#!/usr/bin/env python3
"""SUBZERO quote leftover names sz-paid-validation as QUOTE_DRAFT, not cash."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from subzero_quote import (
    ALREADY_LANDED,
    CALIBRATION,
    PRESENCE_RECEIPT,
    QUOTE_PRICE,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SKU_ID,
    SLACK_TS,
    classify,
    classify_quote,
    load_arch_sku,
    load_catalog,
    measure_from_rows,
    measure_root,
)


def _complete(**extra):
    facts = {
        "card_present": True,
        "catalog_present": True,
        "door_present": True,
        "arch_present": True,
        "landed_present": list(ALREADY_LANDED),
        "landed_missing": [],
        "found_phrases": list(REQUIRED_PHRASES),
        "sku_id": SKU_ID,
        "price_usd": QUOTE_PRICE,
        "sku_status": "CANDIDATE",
        "sku_class": "QUOTE_DRAFT",
        "arch_price_usd": QUOTE_PRICE,
        "arch_status": "CANDIDATE",
        "collected_cash_usd": 0,
        "cash_state": "NOT_LANDED",
        "demand": "UNKNOWN",
        "runtime_proof": False,
        "structural_only": 31,
        "runtime_measured": 0,
        "customer_ready": 0,
        "claims_cash": False,
        "claims_runtime": False,
        "claims_demand": False,
        "quote_state": "QUOTE_DRAFT",
        "posting_open": True,
        "no_auth": True,
        "no_gate": True,
        "calibration_ok": True,
    }
    facts.update(extra)
    return facts


class TestSubzeroQuote(unittest.TestCase):
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
                "door_present": True,
                "arch_present": True,
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
                "misses": ["ground/SUBZERO_QUOTE.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_cash_claim_is_not_landed(self):
        verdict = classify(measure_from_rows(_complete(claims_cash=True)))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("not cash", verdict["note"].lower())

    def test_runtime_claim_is_not_landed(self):
        verdict = classify(measure_from_rows(_complete(runtime_proof=True)))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("not runtime", verdict["note"].lower())

    def test_demand_claim_is_not_landed(self):
        verdict = classify(measure_from_rows(_complete(demand="NAMED_INBOUND")))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("not demand", verdict["note"].lower())

    def test_wrong_price_is_not_landed(self):
        verdict = classify(measure_from_rows(_complete(price_usd=30000)))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("2500", verdict["note"])

    def test_quote_draft_is_not_cash(self):
        verdict = classify_quote(
            {
                "measured": True,
                "sku_id": SKU_ID,
                "price_usd": QUOTE_PRICE,
                "sku_class": "QUOTE_DRAFT",
                "demand": "UNKNOWN",
                "structural_only": 31,
                "runtime_measured": 0,
                "customer_ready": 0,
                "runtime_proof": False,
                "collected_cash_usd": 0,
            }
        )
        self.assertEqual(verdict["state"], "QUOTE_DRAFT")
        self.assertIn("not cash", verdict["note"].lower())

    def test_failed_finder_is_not_zero(self):
        verdict = classify_quote(
            {
                "measured": True,
                "finder": "failed",
                "sku_id": SKU_ID,
            }
        )
        self.assertEqual(verdict["state"], "FINDER-FAILED")
        self.assertIn("never 0", verdict["note"].lower())

    def test_complete_leftover_is_integrated(self):
        verdict = classify(measure_from_rows(_complete()))
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_live_tree_has_the_leftover(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["landed_missing"], [])
        self.assertEqual(row["sku_id"], SKU_ID)
        self.assertEqual(row["price_usd"], QUOTE_PRICE)
        self.assertEqual(row["sku_class"], "QUOTE_DRAFT")
        self.assertEqual(row["arch_price_usd"], QUOTE_PRICE)
        self.assertEqual(row["arch_status"], "CANDIDATE")
        self.assertEqual(row["collected_cash_usd"], 0)
        self.assertEqual(row["demand"], "UNKNOWN")
        self.assertFalse(row["runtime_proof"])
        self.assertEqual(row["structural_only"], 31)
        self.assertEqual(row["runtime_measured"], 0)
        self.assertEqual(row["customer_ready"], 0)
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787649732.551439")
        self.assertEqual(PRESENCE_RECEIPT, "rivet-ship-subzero-tech-presence-20260825-01")
        self.assertEqual(len(CALIBRATION), 3)
        self.assertGreaterEqual(len(SEARCH_SPACE), 10)
        with open(os.path.join(ROOT, "ground", "SUBZERO_QUOTE.json"), encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["sku_id"], SKU_ID)
        self.assertEqual(catalog["sku_class"], "QUOTE_DRAFT")
        self.assertEqual(catalog["collected_cash_usd"], 0)
        self.assertFalse(catalog["runtime_proof"])
        with open(
            os.path.join(ROOT, "revenue", "subzero_gtm", "architecture.json"),
            encoding="utf-8",
        ) as handle:
            arch = load_arch_sku(handle.read())
        self.assertEqual(arch["id"], SKU_ID)
        self.assertEqual(arch["price_usd"], QUOTE_PRICE)
        self.assertEqual(arch["status"], "CANDIDATE")
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
