#!/usr/bin/env python3
"""latch-owner-now-wb-hour-restore-20260919-01 — existing WB hour Buy CTA."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "owner-now-revenue.html"
RECEIPT = ROOT / "p" / "latch-owner-now-wb-hour-restore-20260919-01.md"
ACTION = ROOT / "p" / "action-20260919110812-22a675665683.md"
BUY_URL = "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07"
AUTOPSY = "4gM9AS3Ot8bfeOZ78S43S0g"
BUY_HOST_PATH = re.compile(
    r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)


class TestLatchOwnerNowWbHourRestore2026091901(unittest.TestCase):
    def test_owner_now_exposes_exactly_the_existing_whitebox_hour_buy(self) -> None:
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="buy-now-live-checkout"', html)
        self.assertIn(BUY_URL, html)
        self.assertIn("Buy one White Box hour $250", html)
        found = {
            "https://buy.stripe.com/%s" % path
            for path in BUY_HOST_PATH.findall(html)
        }
        self.assertEqual(found, {BUY_URL})
        self.assertNotIn(AUTOPSY, html)
        self.assertNotIn("donate.stripe.com", html)
        live_cash = html.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", live_cash)
        noscript = html.split("<noscript>", 1)[1].split("</noscript>", 1)[0]
        self.assertNotIn("buy.stripe.com", noscript)
        self.assertIn("sku-whitebox-hour", html)
        self.assertIn("anvil-ownerrevenue-paidopps-convert-shelf-20260917-01", html)

    def test_receipt_cites_action_and_existing_payment_link(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: latch-owner-now-wb-hour-restore-20260919-01", text)
        self.assertIn("action-20260919110812-22a675665683", text)
        self.assertIn(BUY_URL, text)
        self.assertIn("sku-whitebox-hour", text)
        self.assertIn("anvil-ownerrevenue-paidopps-convert-shelf-20260917-01", text)
        self.assertIn("Autopsy SCRAPPED", text)
        self.assertIn("Did not remint", text)
        self.assertIn("already DURABLE_PAGE", text)
        self.assertNotIn("First-minted action-20260919110812", text)
        self.assertNotIn(AUTOPSY, text)
        self.assertNotIn("id: grok-seat-carry-work-20260919-02", text)

    def test_action_canonical_body_was_not_reminted(self) -> None:
        text = ACTION.read_text(encoding="utf-8")
        self.assertIn("id: action-20260919110812-22a675665683", text)
        self.assertIn("carrier: ntfy", text)
        self.assertIn("state: DURABLE_PAGE", text)
        self.assertIn("Grok seat jumped in 2026-09-19", text)
        self.assertNotIn(AUTOPSY, text)


if __name__ == "__main__":
    unittest.main()
