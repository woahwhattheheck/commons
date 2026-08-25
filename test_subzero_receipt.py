#!/usr/bin/env python3
"""H-008 leftover: quote-draft → buyer-bound receipt, not cash."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from subzero_receipt import (
    ALREADY_LANDED,
    CALIBRATION,
    CELL,
    GRBN_REL,
    GRBN_SHA,
    HUMAN_RECEIPT,
    P01_ID,
    QUOTE_PRICE,
    QUOTE_RECEIPT,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SKU_ID,
    SLACK_TS,
    bind_validation_receipt,
    classify,
    classify_binding,
    measure_from_rows,
    measure_root,
    receipt_schema_ok,
    source_index,
)


def _complete(**extra):
    facts = {
        "card_present": True,
        "catalog_present": True,
        "door_present": True,
        "quote_present": True,
        "arch_present": True,
        "buyers_present": True,
        "schema_present": True,
        "landed_present": list(ALREADY_LANDED),
        "landed_missing": [],
        "found_phrases": list(REQUIRED_PHRASES),
        "sku_id": SKU_ID,
        "quote_class": "QUOTE_DRAFT",
        "quote_price": QUOTE_PRICE,
        "p01_id": P01_ID,
        "arch_status": "CANDIDATE",
        "arch_implements": P01_ID,
        "schema_has_buyer": True,
        "schema_no_auth": True,
        "schema_no_gate": True,
        "binding_state": "UNBOUND",
        "live_bound_receipts": 0,
        "bind_works": True,
        "grbn_sha": GRBN_SHA,
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
        "posting_open": True,
        "no_auth": True,
        "no_gate": True,
        "calibration_ok": True,
    }
    facts.update(extra)
    return facts


class TestSubzeroReceipt(unittest.TestCase):
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
                "misses": ["ground/SUBZERO_RECEIPT.md"],
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

    def test_invented_live_buyer_is_not_landed(self):
        verdict = classify(measure_from_rows(_complete(live_bound_receipts=1)))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("invented", verdict["note"].lower())

    def test_missing_inbound_stays_unbound(self):
        got = bind_validation_receipt(
            ROOT, "missing-inbound-does-not-exist-20260825-01", GRBN_REL
        )
        self.assertEqual(got["binding_state"], "UNBOUND")
        self.assertFalse(got["receipt"]["bound"])
        self.assertEqual(got["receipt"]["buyer_id"], "")
        self.assertEqual(got["evidence_class"], "STRUCTURAL_ONLY")
        self.assertEqual(got["cash_state"], "NOT_LANDED")
        self.assertEqual(got["demand"], "UNKNOWN")

    def test_public_inbound_can_bind_without_claiming_cash(self):
        got = bind_validation_receipt(ROOT, QUOTE_RECEIPT, GRBN_REL, status="PASS")
        self.assertEqual(got["binding_state"], "BUYER_BOUND")
        self.assertTrue(got["receipt"]["bound"])
        self.assertEqual(got["receipt"]["buyer_id"], QUOTE_RECEIPT)
        self.assertEqual(got["receipt"]["status"], "UNKNOWN")
        self.assertEqual(got["receipt"]["sha256"], GRBN_SHA)
        self.assertTrue(receipt_schema_ok(got["receipt"]))
        self.assertEqual(got["evidence_class"], "STRUCTURAL_ONLY")
        self.assertEqual(got["cash_state"], "NOT_LANDED")
        self.assertEqual(got["demand"], "UNKNOWN")

    def test_failed_finder_is_not_zero(self):
        verdict = classify_binding(
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
        self.assertEqual(row["quote_price"], QUOTE_PRICE)
        self.assertEqual(row["quote_class"], "QUOTE_DRAFT")
        self.assertEqual(row["p01_id"], P01_ID)
        self.assertEqual(row["arch_implements"], P01_ID)
        self.assertEqual(row["arch_status"], "CANDIDATE")
        self.assertTrue(row["schema_has_buyer"])
        self.assertTrue(row["bind_works"])
        self.assertEqual(row["binding_state"], "UNBOUND")
        self.assertEqual(row["live_bound_receipts"], 0)
        self.assertEqual(row["collected_cash_usd"], 0)
        self.assertEqual(row["demand"], "UNKNOWN")
        self.assertFalse(row["runtime_proof"])
        self.assertEqual(row["structural_only"], 31)
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787650230.035359")
        self.assertEqual(CELL, "H-008")
        self.assertEqual(QUOTE_RECEIPT, "rivet-ship-subzero-quote-20260825-01")
        self.assertEqual(HUMAN_RECEIPT, "rivet-ship-human-outcomes-20260825-01")
        self.assertEqual(len(CALIBRATION), 3)
        self.assertGreaterEqual(len(SEARCH_SPACE), 10)
        indexed = source_index(ROOT)
        self.assertEqual(indexed["sku_id"], SKU_ID)
        self.assertEqual(indexed["quote_class"], "QUOTE_DRAFT")
        self.assertEqual(indexed["p01_id"], P01_ID)
        self.assertEqual(indexed["arch_implements"], P01_ID)
        self.assertTrue(indexed["schema_has_buyer"])
        self.assertEqual(indexed["collected_cash_usd"], 0)
        self.assertFalse(indexed["runtime_proof"])
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "p", HUMAN_RECEIPT + ".md")))
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
