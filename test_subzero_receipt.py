#!/usr/bin/env python3
"""H-009 leftover: H-008 binder is not buyer-bound until acceptance."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from subzero_receipt import (
    ALREADY_LANDED,
    AUDITED_TREE,
    AUDIT_SLACK_TS,
    CALIBRATION,
    CELL,
    GRBN_REL,
    GRBN_SHA,
    HDVS_REL,
    HUMAN_RECEIPT,
    P01_ID,
    QUOTE_PRICE,
    QUOTE_RECEIPT,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SKU_ID,
    SLACK_TS,
    acceptance_fixture,
    bind_validation_receipt,
    classify,
    classify_binding,
    inbound_rel,
    measure_from_rows,
    measure_root,
    present_int,
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
        "quote_price_state": "PRESENT",
        "quote_hash": "a" * 64,
        "catalog_row_hash": "b" * 64,
        "p01_id": P01_ID,
        "arch_status": "CANDIDATE",
        "arch_implements": P01_ID,
        "schema_has_buyer": True,
        "schema_no_auth": True,
        "schema_no_gate": True,
        "binding_state": "UNBOUND",
        "legal_state": "DRAFT",
        "live_bound_receipts": 0,
        "bind_works": True,
        "grbn_sha": GRBN_SHA,
        "collected_cash_usd": 0,
        "collected_cash_state": "PRESENT",
        "cash_state": "NOT_LANDED",
        "demand": "UNKNOWN",
        "runtime_proof": False,
        "structural_only": 31,
        "structural_only_state": "PRESENT",
        "runtime_measured": 0,
        "runtime_measured_state": "PRESENT",
        "customer_ready": 0,
        "customer_ready_state": "PRESENT",
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

    def test_missing_numeric_field_is_unresolved_not_zero(self):
        self.assertIsNone(present_int({}, "price_usd"))
        self.assertIsNone(present_int({"price_usd": None}, "price_usd"))
        self.assertIsNone(present_int({"price_usd": ""}, "price_usd"))
        self.assertIsNone(present_int({"price_usd": "nope"}, "price_usd"))
        self.assertEqual(present_int({"price_usd": 0}, "price_usd"), 0)
        self.assertEqual(present_int({"price_usd": 2500}, "price_usd"), 2500)
        verdict = classify_binding(
            {
                "measured": True,
                "sku_id": SKU_ID,
                "quote_price": None,
                "quote_price_state": "UNRESOLVED",
                "collected_cash_state": "PRESENT",
                "structural_only_state": "PRESENT",
                "runtime_measured_state": "PRESENT",
                "customer_ready_state": "PRESENT",
                "p01_id": P01_ID,
                "schema_has_buyer": True,
                "bind_works": True,
                "binding_state": "UNBOUND",
                "legal_state": "DRAFT",
            }
        )
        self.assertEqual(verdict["state"], "FINDER-FAILED")
        self.assertIn("unresolved", verdict["note"].lower())

    def test_windows_traversal_stays_unbound(self):
        got = bind_validation_receipt(ROOT, "..\\ground\\EXECUTE", GRBN_REL)
        self.assertEqual(inbound_rel("..\\ground\\EXECUTE", root=ROOT), "")
        self.assertFalse(got["inbound_path_ok"])
        self.assertEqual(got["binding_state"], "UNBOUND")
        self.assertEqual(got["bind_reason"], "INVALID_INBOUND_ID")
        self.assertEqual(got["receipt"]["buyer_id"], "")
        self.assertEqual(got["legal_state"], "DRAFT")

    def test_forward_slash_traversal_stays_unbound(self):
        got = bind_validation_receipt(ROOT, "../ground/EXECUTE", GRBN_REL)
        self.assertEqual(got["binding_state"], "UNBOUND")
        self.assertEqual(got["bind_reason"], "INVALID_INBOUND_ID")

    def test_project_quote_receipt_is_not_a_buyer(self):
        got = bind_validation_receipt(ROOT, QUOTE_RECEIPT, GRBN_REL, status="PASS")
        self.assertEqual(got["binding_state"], "UNBOUND")
        self.assertEqual(got["bind_reason"], "PROJECT_RECEIPT_NOT_BUYER")
        self.assertEqual(got["receipt"]["buyer_id"], "")
        self.assertEqual(got["receipt"]["status"], "UNKNOWN")
        self.assertEqual(got["evidence_class"], "STRUCTURAL_ONLY")
        self.assertEqual(got["cash_state"], "NOT_LANDED")
        self.assertEqual(got["demand"], "UNKNOWN")

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

    def test_existing_post_without_acceptance_is_not_buyer_bound(self):
        got = bind_validation_receipt(ROOT, HUMAN_RECEIPT, GRBN_REL)
        self.assertEqual(got["binding_state"], "UNBOUND")
        self.assertIn(got["bind_reason"], {"PROJECT_RECEIPT_NOT_BUYER", "FILE_IS_NOT_ACCEPTANCE"})

    def test_pass_refused_on_grbn_and_other_excerpt(self):
        grbn = bind_validation_receipt(ROOT, QUOTE_RECEIPT, GRBN_REL, status="PASS")
        hdvs = bind_validation_receipt(ROOT, QUOTE_RECEIPT, HDVS_REL, status="PASS")
        self.assertEqual(grbn["receipt"]["status"], "UNKNOWN")
        self.assertEqual(hdvs["receipt"]["status"], "UNKNOWN")
        self.assertTrue(hdvs["excerpt_ok"])

    def test_acceptance_fixture_can_bind_without_claiming_cash(self):
        quote_hash = source_index(ROOT)["quote_hash"]
        got = bind_validation_receipt(
            ROOT,
            "fixture-buyer-accept-20260825-01",
            GRBN_REL,
            status="PASS",
            post_text=acceptance_fixture(quote_hash),
        )
        self.assertEqual(got["binding_state"], "BUYER_BOUND")
        self.assertTrue(got["receipt"]["bound"])
        self.assertEqual(got["receipt"]["buyer_id"], "fixture-buyer-accept-20260825-01")
        self.assertEqual(got["receipt"]["status"], "UNKNOWN")
        self.assertEqual(got["legal_state"], "ACCEPTED")
        self.assertEqual(got["receipt"]["sha256"], GRBN_SHA)
        self.assertEqual(got["receipt"]["source_tree"], AUDITED_TREE)
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
        self.assertEqual(row["quote_price_state"], "PRESENT")
        self.assertEqual(row["quote_class"], "QUOTE_DRAFT")
        self.assertEqual(row["p01_id"], P01_ID)
        self.assertEqual(row["arch_implements"], P01_ID)
        self.assertEqual(row["arch_status"], "CANDIDATE")
        self.assertTrue(row["schema_has_buyer"])
        self.assertTrue(row["bind_works"])
        self.assertEqual(row["binding_state"], "UNBOUND")
        self.assertEqual(row["legal_state"], "DRAFT")
        self.assertEqual(row["live_bound_receipts"], 0)
        self.assertEqual(row["collected_cash_usd"], 0)
        self.assertEqual(row["collected_cash_state"], "PRESENT")
        self.assertEqual(row["demand"], "UNKNOWN")
        self.assertFalse(row["runtime_proof"])
        self.assertEqual(row["structural_only"], 31)
        self.assertNotIn("titan", row)
        self.assertEqual(SLACK_TS, "1787650230.035359")
        self.assertEqual(AUDIT_SLACK_TS, "1787651030.360809")
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
        self.assertEqual(indexed["quote_price_state"], "PRESENT")
        self.assertFalse(indexed["runtime_proof"])
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "p", HUMAN_RECEIPT + ".md")))
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
