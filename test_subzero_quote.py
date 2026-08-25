#!/usr/bin/env python3
"""SUBZERO quote leftover names sz-paid-validation as QUOTE_DRAFT, not cash."""

from __future__ import annotations

import json
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from subzero_quote import (
    ALREADY_LANDED,
    CALIBRATION,
    H009_TS,
    PRESENCE_RECEIPT,
    QUOTE_PRICE,
    QUOTE_RECEIPT,
    REQUIRED_PHRASES,
    SEARCH_SPACE,
    SKU_ID,
    SLACK_TS,
    _posix_parts as quote_posix_parts,
    classify,
    classify_quote,
    inbound_rel,
    legal_state_for,
    load_arch_sku,
    load_catalog,
    measure_from_rows,
    measure_root,
    present_int,
    public_inbound,
    safe_rel,
    titan_lock_fields,
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
        "legal_state": "NEEDS_BUYER",
        "inbound_state": "EMPTY",
        "holes_closed": True,
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

    def test_missing_price_is_finder_failed(self):
        verdict = classify_quote(
            {
                "measured": True,
                "sku_id": SKU_ID,
                "sku_class": "QUOTE_DRAFT",
                "demand": "UNKNOWN",
                "structural_only": 31,
                "runtime_measured": 0,
                "customer_ready": 0,
                "collected_cash_usd": 0,
            }
        )
        self.assertEqual(verdict["state"], "FINDER-FAILED")
        self.assertIn("missing numeric", verdict["note"].lower())

    def test_present_int_never_coerces_zero(self):
        self.assertEqual(present_int({}, "price_usd")["state"], "UNRESOLVED")
        self.assertIsNone(present_int({}, "price_usd")["value"])
        self.assertEqual(present_int({"price_usd": None}, "price_usd")["state"], "UNRESOLVED")
        self.assertEqual(present_int({"price_usd": True}, "price_usd")["state"], "FINDER-FAILED")
        self.assertEqual(present_int({"price_usd": 2500}, "price_usd")["value"], 2500)

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

    def test_windows_path_stays_out_of_p(self):
        self.assertEqual(inbound_rel("..\\ground\\EXECUTE"), "")
        self.assertEqual(inbound_rel("../ground/EXECUTE"), "")
        self.assertEqual(public_inbound("..\\ground\\EXECUTE")["state"], "TRAVERSAL")
        self.assertEqual(public_inbound(QUOTE_RECEIPT)["state"], "SELF_BIND")
        self.assertEqual(public_inbound("")["state"], "EMPTY")
        self.assertEqual(safe_rel("..\\ground\\EXECUTE.md"), "")
        self.assertEqual(safe_rel("../ground/EXECUTE.md"), "")
        self.assertEqual(safe_rel("C:\\Windows\\system32"), "")
        self.assertEqual(safe_rel("ground/SUBZERO_QUOTE.md"), "ground/SUBZERO_QUOTE.md")

    def test_trusted_windows_separator_normalizes_without_inbound_escape(self):
        self.assertEqual(quote_posix_parts("ground\\HEAD.md"), ["ground", "HEAD.md"])
        self.assertEqual(quote_posix_parts("..\\ground\\HEAD.md"), [])
        self.assertEqual(inbound_rel("..\\ground\\EXECUTE"), "")
        self.assertEqual(safe_rel("ground\\HEAD.md"), "")

    def test_legal_state_is_not_leftover_integrated(self):
        self.assertEqual(legal_state_for({}, inbound_bound=False), "DRAFT")
        self.assertEqual(
            legal_state_for({"quote_hash": "a" * 64}, inbound_bound=False),
            "NEEDS_BUYER",
        )
        self.assertEqual(
            legal_state_for({"quote_hash": "a" * 64}, inbound_bound=True),
            "ACCEPTED",
        )
        fused = classify(measure_from_rows(_complete(legal_state="ACCEPTED")))
        self.assertEqual(fused["state"], "NOT_LANDED")
        self.assertIn("NEEDS_BUYER", fused["note"])

    def test_titan_lock_fields_are_not_health(self):
        self.assertEqual(
            titan_lock_fields({"titan": "NOT_WRITTEN"}, ""),
            ["catalog.titan=NOT_WRITTEN"],
        )
        self.assertIn(
            "catalog.hands_off:titan --go",
            titan_lock_fields({"hands_off": ["PR 2108", "titan --go"]}, ""),
        )
        self.assertIn(
            "catalog.collision_avoidance:titan --go",
            titan_lock_fields({"collision_avoidance": ["PR 2108", "titan --go"]}, ""),
        )
        self.assertEqual(
            titan_lock_fields({}, "Hands off CML PR 2108, SPECTER, titan `--go`."),
            ["card:hands-off-titan"],
        )
        self.assertEqual(titan_lock_fields({}, "Titan skip is not health."), [])
        locked = classify(
            measure_from_rows(
                _complete(titan_lock_fields=["catalog.titan=NOT_WRITTEN"])
            )
        )
        self.assertEqual(locked["state"], "NOT_LANDED")
        self.assertIn("titan lock/health", locked["note"].lower())

    def test_complete_leftover_is_integrated(self):
        verdict = classify(measure_from_rows(_complete()))
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])
        self.assertIn("H-009", verdict["note"])
        self.assertIn("NEEDS_BUYER", verdict["note"])

    def test_live_tree_has_the_leftover(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["landed_missing"], [])
        self.assertEqual(row["sku_id"], SKU_ID)
        self.assertEqual(row["price_usd"], QUOTE_PRICE)
        self.assertEqual(row["price_usd_state"], "PRESENT")
        self.assertEqual(row["sku_class"], "QUOTE_DRAFT")
        self.assertEqual(row["arch_price_usd"], QUOTE_PRICE)
        self.assertEqual(row["arch_status"], "CANDIDATE")
        self.assertEqual(row["collected_cash_usd"], 0)
        self.assertEqual(row["collected_cash_state"], "PRESENT")
        self.assertEqual(row["demand"], "UNKNOWN")
        self.assertFalse(row["runtime_proof"])
        self.assertEqual(row["structural_only"], 31)
        self.assertEqual(row["runtime_measured"], 0)
        self.assertEqual(row["customer_ready"], 0)
        self.assertIn(row["legal_state"], ("DRAFT", "NEEDS_BUYER"))
        self.assertEqual(row["inbound_state"], "EMPTY")
        self.assertTrue(row["holes_closed"])
        self.assertEqual(row.get("titan_lock_fields"), [])
        self.assertNotIn("titan", row)
        self.assertEqual(row["hashes"].get("delivery_hash"), "UNRESOLVED")
        self.assertEqual(len(row["hashes"].get("source_commit") or ""), 40)
        self.assertEqual(SLACK_TS, "1787649732.551439")
        self.assertEqual(H009_TS, "1787651627.535699")
        self.assertEqual(PRESENCE_RECEIPT, "rivet-ship-subzero-tech-presence-20260825-01")
        self.assertEqual(len(CALIBRATION), 3)
        self.assertGreaterEqual(len(SEARCH_SPACE), 10)
        with open(os.path.join(ROOT, "ground", "SUBZERO_QUOTE.json"), encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["sku_id"], SKU_ID)
        self.assertEqual(catalog["sku_class"], "QUOTE_DRAFT")
        self.assertEqual(catalog["collected_cash_usd"], 0)
        self.assertEqual(catalog["price_usd_state"], "PRESENT")
        self.assertFalse(catalog["runtime_proof"])
        self.assertNotIn("titan", catalog)
        with open(os.path.join(ROOT, "ground", "SUBZERO_QUOTE.json"), encoding="utf-8") as handle:
            raw_catalog = json.loads(handle.read())
        with open(os.path.join(ROOT, "ground", "SUBZERO_QUOTE.md"), encoding="utf-8") as handle:
            raw_card = handle.read()
        self.assertNotIn("titan", raw_catalog)
        self.assertNotIn("hands_off", raw_catalog)
        self.assertNotIn("titan --go", raw_catalog.get("collision_avoidance") or [])
        self.assertEqual(titan_lock_fields(raw_catalog, raw_card), [])
        with open(
            os.path.join(ROOT, "revenue", "subzero_gtm", "architecture.json"),
            encoding="utf-8",
        ) as handle:
            arch = load_arch_sku(handle.read())
        self.assertEqual(arch["id"], SKU_ID)
        self.assertEqual(arch["price_usd"], QUOTE_PRICE)
        self.assertEqual(arch["status"], "CANDIDATE")
        verdict = classify(row)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("legal_state", verdict["note"].lower() + " " + row["legal_state"].lower())


if __name__ == "__main__":
    unittest.main()
