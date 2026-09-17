#!/usr/bin/env python3
"""quill-autopsy-sell-receipt-20260917-01 — sell receipt under Wire.

Thin public sell receipt pad pointing at EXISTING Autopsy $29 PL and Wire
storefront autopsy-buy.html. No remint. No invent Stripe. Tip KEEP. #8802 off.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p" / "quill-autopsy-sell-receipt-20260917-01.md"
STOREFRONT = ROOT / "autopsy-buy.html"
WIRE_RECEIPT = ROOT / "p" / "wire-autopsy-x-storefront-20260917-01.md"
SELL_HTML = ROOT / "autopsy-sell-receipt.html"

AUTOPSY_PL = "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g"
CLAIM = "quill-autopsy-sell-receipt-20260917-01"


class TestQuillAutopsySellReceipt2026091701(unittest.TestCase):
    def test_receipt_is_sell_share_card_with_buy_first(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(f"id: {CLAIM}", text)
        self.assertIn("from: QUILL", text)
        buy_at = text.find("**Buy Autopsy $29**")
        storefront_at = text.find("autopsy-buy.html")
        self.assertGreater(buy_at, -1)
        self.assertGreater(storefront_at, buy_at)
        self.assertIn(AUTOPSY_PL, text)
        self.assertIn("≠ Wire autopsy-buy remint", text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("#8802 off", text)
        self.assertIn("No invent Stripe", text)
        self.assertIn("No X", text)
        self.assertIn("No Muse", text)
        self.assertNotIn("donate.stripe.com", text)

    def test_wire_storefront_still_owns_door_with_exact_pl(self) -> None:
        html = STOREFRONT.read_text(encoding="utf-8")
        self.assertIn("<h1>Agent Failure Autopsy — $29</h1>", html)
        self.assertIn("Buy Autopsy $29", html)
        self.assertIn(AUTOPSY_PL, html)
        self.assertTrue(WIRE_RECEIPT.is_file())
        wire = WIRE_RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: wire-autopsy-x-storefront-20260917-01", wire)
        self.assertIn(AUTOPSY_PL, wire)

    def test_no_receipt_html_remint(self) -> None:
        self.assertFalse(
            SELL_HTML.exists(),
            "autopsy-sell-receipt.html must not remint Wire autopsy-buy door",
        )


if __name__ == "__main__":
    unittest.main()
