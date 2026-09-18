#!/usr/bin/env python3
"""Hermetic: newbot-goat-sidewalk-larger-fixed-20260916-23 — KEEP Larger fixed on DOOR_LIVE_CASH_V1."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "newbot-goat-sidewalk-larger-fixed-20260916-23"
sys.path.insert(0, str(ROOT / "host"))
import goat_sidewalk_door_match as match  # noqa: E402

PRODUCTS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER = ("diagnostic.html", "commercial.html")


class TestNewbotGoatSidewalkLargerFixed2026091623(unittest.TestCase):
    def test_door_live_cash_v1_has_autopsy_and_larger_fixed(self) -> None:
        blob = match.DOOR_LIVE_CASH_V1.decode("utf-8")
        self.assertIn('id="live-cash"', blob)


        for name in PRODUCTS:
            self.assertIn(f"../../{name}", blob)
        self.assertIn("Larger fixed engagements", blob)
        self.assertIn("../../diagnostic.html", blob)
        self.assertIn("../../commercial.html", blob)
        self.assertIn("$12,000", blob)
        self.assertIn("$30,000", blob)
        self.assertNotIn("buy.stripe.com", blob)
        self.assertNotIn("plink_", blob)

    def test_pack_door_matches_door_live_cash_v1(self) -> None:
        door = (ROOT / match.DOOR_REL).read_bytes()
        self.assertIn(match.DOOR_LIVE_CASH_V1, door)
        text = door.decode("utf-8")
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("../../diagnostic.html", text)
        self.assertIn("../../commercial.html", text)
        self.assertNotIn("buy.stripe.com", text.split('id="live-cash"', 1)[1].split('</section>', 1)[0])

    def test_checkout_still_not_minted(self) -> None:
        self.assertEqual(match.checkout_status(), "NOT_MINTED")
        checkout = (ROOT / "packs/sidewalk-signal-web-desk-20260902-01/checkout.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("status: NOT_MINTED", checkout)

    def test_product_pages_exist(self) -> None:
        for name in PRODUCTS + LARGER:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_door_successor_and_checkout_ok(self) -> None:
        result = match.classify_match()
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertEqual(result["door_baseline_blob"], match.DOOR_BLOB)
        self.assertIn("live-cash-v1", result["door_successors"])
        self.assertTrue(result["did_not_write_pack"])
        self.assertTrue(result["did_not_remint_pages_allowlist"])

    def test_receipt_exists(self) -> None:
        receipt = ROOT / "p" / f"{CLAIM}.md"
        self.assertTrue(receipt.is_file())
        text = receipt.read_text(encoding="utf-8")
        self.assertIn(CLAIM, text)
        self.assertIn("host/goat_sidewalk_door_match.py", text)
        self.assertIn("diagnostic.html", text)
        self.assertIn("commercial.html", text)


if __name__ == "__main__":
    unittest.main()
