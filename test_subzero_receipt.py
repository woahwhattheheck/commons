#!/usr/bin/env python3
"""H-008 leftover + JOJO second pass: bind holes closed, not cash."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from subzero_receipt import (
    _posix_parts as receipt_posix_parts,
    ALREADY_LANDED,
    CALIBRATION,
    CELL,
    FIRST_RECEIPT,
    GRBN_REL,
    GRBN_SHA,
    HARDENING_TS,
    HUMAN_RECEIPT,
    LVIN_REL,
    P01_ID,
    QUOTE_PRICE,
    QUOTE_RECEIPT,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SECOND_PASS_TS,
    SKU_ID,
    SLACK_TS,
    bind_validation_receipt,
    canonicalize_post_id,
    classify,
    classify_binding,
    inbound_rel,
    inbound_semantic,
    measure_from_rows,
    measure_root,
    present_int,
    safe_rel,
    receipt_schema_ok,
    sha256_rel,
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
        "p01_id": P01_ID,
        "arch_status": "CANDIDATE",
        "arch_implements": P01_ID,
        "schema_has_buyer": True,
        "schema_no_auth": True,
        "schema_no_gate": True,
        "binding_state": "CANDIDATE",
        "legal_state": "NEEDS_BUYER",
        "live_bound_receipts": 0,
        "live_bound_receipts_state": "PRESENT",
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
    def test_trusted_windows_separator_normalizes_without_inbound_escape(self):
        self.assertEqual(receipt_posix_parts("ground\\HEAD.md"), ["ground", "HEAD.md"])
        self.assertEqual(receipt_posix_parts("..\\ground\\HEAD.md"), [])
        self.assertEqual(inbound_rel("..\\ground\\EXECUTE"), "")

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
        self.assertEqual(got["legal_state"], "NEEDS_BUYER")
        self.assertEqual(got["evidence_class"], "STRUCTURAL_ONLY")
        self.assertEqual(got["cash_state"], "NOT_LANDED")
        self.assertEqual(got["demand"], "UNKNOWN")

    def test_windows_backslash_traversal_is_not_bound(self):
        got = bind_validation_receipt(ROOT, "..\\ground\\EXECUTE", GRBN_REL, status="PASS")
        self.assertEqual(inbound_rel("..\\ground\\EXECUTE"), "")
        self.assertFalse(got["inbound_ok"])
        self.assertFalse(got["receipt"]["bound"])
        self.assertNotEqual(got["binding_state"], "BUYER_BOUND")
        self.assertEqual(got["buyer_reason"], "INVALID_ID")
        self.assertEqual(got["status_refused"], "PASS_WITHOUT_BUYER")
        self.assertEqual(got["receipt"]["status"], "UNKNOWN")

    def test_quote_receipt_is_self_bind_not_buyer(self):
        got = bind_validation_receipt(ROOT, QUOTE_RECEIPT, GRBN_REL, status="PASS")
        self.assertFalse(got["inbound_ok"])
        self.assertFalse(got["receipt"]["bound"])
        self.assertEqual(got["binding_state"], "UNBOUND")
        self.assertEqual(got["buyer_reason"], "SELF_BIND")
        self.assertEqual(got["receipt"]["buyer_id"], "")
        self.assertEqual(got["receipt"]["status"], "UNKNOWN")
        self.assertEqual(got["legal_state"], "NEEDS_BUYER")
        self.assertTrue(receipt_schema_ok(got["receipt"]))
        self.assertEqual(got["evidence_class"], "STRUCTURAL_ONLY")
        self.assertEqual(got["cash_state"], "NOT_LANDED")
        self.assertEqual(got["demand"], "UNKNOWN")

    def test_existing_unrelated_post_is_not_a_public_inbound(self):
        got = bind_validation_receipt(
            ROOT,
            "bryce-action-pad-open-door-directive-20260822-01",
            GRBN_REL,
            status="PASS",
        )
        self.assertFalse(got["inbound_ok"])
        self.assertFalse(got["receipt"]["bound"])
        self.assertEqual(got["binding_state"], "UNBOUND")
        self.assertEqual(got["buyer_reason"], "IRRELEVANT_INBOUND")
        self.assertEqual(got["status_refused"], "PASS_WITHOUT_BUYER")

    def test_relevant_inbound_without_acceptance_is_incomplete(self):
        inbound_id = "fixture-quote-mention-sz-20260825-01"
        tmp = tempfile.mkdtemp(prefix="subzero-receipt-relevant-")
        try:
            os.makedirs(os.path.join(tmp, "p"))
            os.makedirs(os.path.join(tmp, "excerpts", "20260823"))
            os.makedirs(os.path.join(tmp, "ground"))
            shutil.copyfile(
                os.path.join(ROOT, "excerpts", "20260823", "muhl_grbn.mno"),
                os.path.join(tmp, "excerpts", "20260823", "muhl_grbn.mno"),
            )
            shutil.copyfile(
                os.path.join(ROOT, "ground", "SUBZERO_QUOTE.json"),
                os.path.join(tmp, "ground", "SUBZERO_QUOTE.json"),
            )
            with open(os.path.join(tmp, "p", inbound_id + ".md"), "w", encoding="utf-8") as handle:
                handle.write(
                    "---\n"
                    "from: FIXTURE_WATCHER\n"
                    "to: TABLE\n"
                    "id: " + inbound_id + "\n"
                    "subject: watching sz-paid-validation\n"
                    "---\n\n"
                    "This public inbound names sz-paid-validation but does not accept.\n"
                )
            got = bind_validation_receipt(tmp, inbound_id, GRBN_REL, status="PASS")
            self.assertTrue(got["inbound_ok"])
            self.assertFalse(got["receipt"]["bound"])
            self.assertEqual(got["binding_state"], "INCOMPLETE")
            self.assertEqual(got["buyer_reason"], "NO_ACCEPTANCE")
            self.assertEqual(got["status_refused"], "PASS_WITHOUT_BUYER")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_pass_refused_on_non_grbn_excerpt(self):
        got = bind_validation_receipt(ROOT, QUOTE_RECEIPT, LVIN_REL, status="PASS")
        self.assertTrue(got["excerpt_ok"])
        self.assertNotEqual(got["receipt"].get("sha256"), GRBN_SHA)
        self.assertFalse(got["receipt"]["bound"])
        self.assertEqual(got["status_refused"], "PASS_WITHOUT_BUYER")
        self.assertEqual(got["receipt"]["status"], "UNKNOWN")

    def test_missing_numeric_is_unresolved_not_zero(self):
        missing = present_int({}, "price_usd")
        blank = present_int({"price_usd": None}, "price_usd")
        bad = present_int({"price_usd": True}, "price_usd")
        present = present_int({"price_usd": 2500}, "price_usd")
        self.assertEqual(missing["state"], "UNRESOLVED")
        self.assertIsNone(missing["value"])
        self.assertEqual(blank["state"], "UNRESOLVED")
        self.assertEqual(bad["state"], "FINDER-FAILED")
        self.assertEqual(present["state"], "PRESENT")
        self.assertEqual(present["value"], 2500)
        verdict = classify_binding(
            {
                "measured": True,
                "sku_id": SKU_ID,
                "quote_price": None,
                "quote_price_state": "UNRESOLVED",
                "p01_id": P01_ID,
                "schema_has_buyer": True,
                "bind_works": True,
                "binding_state": "CANDIDATE",
                "collected_cash_usd": 0,
                "collected_cash_state": "PRESENT",
                "live_bound_receipts": 0,
                "live_bound_receipts_state": "PRESENT",
            }
        )
        self.assertEqual(verdict["state"], "FINDER-FAILED")
        self.assertIn("unresolved", verdict["note"].lower())

    def test_fixture_buyer_can_bind_without_claiming_cash(self):
        quote_hash = sha256_rel(ROOT, os.path.join("ground", "SUBZERO_QUOTE.json"))
        inbound_id = "fixture-buyer-accept-sz-20260825-01"
        self.assertTrue(canonicalize_post_id(inbound_id))
        tmp = tempfile.mkdtemp(prefix="subzero-receipt-")
        try:
            os.makedirs(os.path.join(tmp, "p"))
            os.makedirs(os.path.join(tmp, "excerpts", "20260823"))
            os.makedirs(os.path.join(tmp, "ground"))
            os.makedirs(os.path.join(tmp, "host"))
            shutil.copyfile(
                os.path.join(ROOT, "excerpts", "20260823", "muhl_grbn.mno"),
                os.path.join(tmp, "excerpts", "20260823", "muhl_grbn.mno"),
            )
            shutil.copyfile(
                os.path.join(ROOT, "ground", "SUBZERO_QUOTE.json"),
                os.path.join(tmp, "ground", "SUBZERO_QUOTE.json"),
            )
            with open(os.path.join(tmp, "p", inbound_id + ".md"), "w", encoding="utf-8") as handle:
                handle.write(
                    "---\n"
                    "from: FIXTURE_BUYER\n"
                    "to: TABLE\n"
                    "id: " + inbound_id + "\n"
                    "subject: BUYER ACCEPT sz-paid-validation\n"
                    "---\n\n"
                    "I accept the sz-paid-validation quote.\n"
                    "quote hash " + quote_hash + "\n"
                )
            got = bind_validation_receipt(tmp, inbound_id, GRBN_REL, status="PASS")
            self.assertTrue(got["inbound_ok"])
            self.assertTrue(got["excerpt_ok"])
            self.assertTrue(got["receipt"]["bound"])
            self.assertEqual(got["binding_state"], "BUYER_BOUND")
            self.assertEqual(got["legal_state"], "ACCEPTED")
            self.assertEqual(got["receipt"]["buyer_id"], inbound_id)
            self.assertEqual(got["receipt"]["status"], "PASS")
            self.assertEqual(got["receipt"]["sha256"], GRBN_SHA)
            self.assertTrue(receipt_schema_ok(got["receipt"]))
            self.assertEqual(got["evidence_class"], "STRUCTURAL_ONLY")
            self.assertEqual(got["cash_state"], "NOT_LANDED")
            self.assertEqual(got["demand"], "UNKNOWN")
            self.assertEqual(got["hashes"]["delivery_hash"], "UNRESOLVED")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

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
        self.assertIn("CANDIDATE/INCOMPLETE", verdict["note"])

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
        self.assertEqual(row["binding_state"], "CANDIDATE")
        self.assertEqual(row["legal_state"], "NEEDS_BUYER")
        self.assertEqual(row["live_bound_receipts"], 0)
        self.assertEqual(row["live_bound_receipts_state"], "PRESENT")
        self.assertEqual(row["collected_cash_usd"], 0)
        self.assertEqual(row["collected_cash_state"], "PRESENT")
        self.assertEqual(row["demand"], "UNKNOWN")
        self.assertFalse(row["runtime_proof"])
        self.assertEqual(row["structural_only"], 31)
        self.assertNotIn("titan", row)
        self.assertEqual(SLACK_TS, "1787650230.035359")
        self.assertEqual(SECOND_PASS_TS, "1787651030.360809")
        self.assertEqual(HARDENING_TS, "1787651639.893089")
        self.assertEqual(CELL, "H-008")
        self.assertEqual(safe_rel("..\\ground\\EXECUTE"), "")
        self.assertEqual(
            inbound_semantic("", QUOTE_RECEIPT, "")["reason"],
            "SELF_BIND",
        )
        self.assertEqual(QUOTE_RECEIPT, "rivet-ship-subzero-quote-20260825-01")
        self.assertEqual(HUMAN_RECEIPT, "rivet-ship-human-outcomes-20260825-01")
        self.assertEqual(FIRST_RECEIPT, "rivet-ship-subzero-receipt-20260825-01")
        self.assertEqual(len(CALIBRATION), 3)
        self.assertGreaterEqual(len(SEARCH_SPACE), 10)
        indexed = source_index(ROOT)
        self.assertEqual(indexed["sku_id"], SKU_ID)
        self.assertEqual(indexed["quote_class"], "QUOTE_DRAFT")
        self.assertEqual(indexed["p01_id"], P01_ID)
        self.assertEqual(indexed["arch_implements"], P01_ID)
        self.assertTrue(indexed["schema_has_buyer"])
        self.assertEqual(indexed["collected_cash_usd"], 0)
        self.assertEqual(indexed["collected_cash_state"], "PRESENT")
        self.assertFalse(indexed["runtime_proof"])
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "p", HUMAN_RECEIPT + ".md")))
        hashes = row.get("hashes") or {}
        self.assertEqual(len(hashes.get("source_commit") or ""), 40)
        self.assertEqual(len(hashes.get("source_tree") or ""), 40)
        self.assertEqual(len(hashes.get("quote_hash") or ""), 64)
        self.assertEqual(len(hashes.get("catalog_row_hash") or ""), 64)
        self.assertEqual(hashes.get("delivery_hash"), "UNRESOLVED")
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
