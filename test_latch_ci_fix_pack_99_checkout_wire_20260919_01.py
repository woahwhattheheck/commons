#!/usr/bin/env python3
"""latch-ci-fix-pack-99-checkout-wire-20260919-01 — door Buy CTA uses the existing PL."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "packs" / "ci-fix-99-20260917-01"
DOOR = PACK / "door.html"
CHECKOUT = PACK / "checkout.md"
WIRE = ROOT / "p" / "latch-ci-fix-pack-99-checkout-wire-20260919-01.md"
SEAT = ROOT / "p" / "latch-seat-cifix-checkout-wire-20260919-01.md"
GROK_SEAT_01 = ROOT / "p" / "grok-seat-carry-work-20260919-01.md"
GROK_SEAT_02 = ROOT / "p" / "grok-seat-carry-work-20260919-02.md"
ACTION = ROOT / "p" / "action-20260919040904-a4550c3af759.md"
ORIG = ROOT / "p" / "latch-ci-fix-pack-99-20260917-01.md"
BUY_URL = "https://buy.stripe.com/6oU9ASfxb6374alfFo43S0A"
PLINK = "plink_1UHCnTATH4EDE7XDKQlMOnLh"
AUTOPSY = "4gM9AS3Ot8bfeOZ78S43S0g"


class TestLatchCiFixPack99CheckoutWire(unittest.TestCase):
    def test_door_buy_cta_is_the_existing_plink(self) -> None:
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn(BUY_URL, door)
        self.assertIn(PLINK, door)
        self.assertIn("ci-fix-pack-99", door)
        self.assertIn('id="checkout"', door)
        self.assertIn("Buy $99 CI-red fix pack", door)
        self.assertNotIn("NOT_MINTED", door)
        self.assertNotIn(AUTOPSY, door)
        self.assertNotIn('id="buy-now-live-checkout"', door)

    def test_checkout_md_records_the_same_url(self) -> None:
        text = CHECKOUT.read_text(encoding="utf-8")
        self.assertIn(BUY_URL, text)
        self.assertIn(PLINK, text)
        self.assertIn("LIVE_PAYMENT_LINK", text)
        self.assertNotIn("NOT_MINTED", text)
        self.assertNotIn(AUTOPSY, text)

    def test_wire_and_seat_receipts_are_first_mints(self) -> None:
        wire = WIRE.read_text(encoding="utf-8")
        seat = SEAT.read_text(encoding="utf-8")
        self.assertIn("id: latch-ci-fix-pack-99-checkout-wire-20260919-01", wire)
        self.assertIn(BUY_URL, wire)
        self.assertIn(PLINK, wire)
        self.assertIn("latch-ci-fix-pack-99-20260917-01", wire)
        self.assertIn("id: latch-seat-cifix-checkout-wire-20260919-01", seat)
        self.assertIn("grok-seat-carry-work-20260919-01", seat)
        self.assertIn(BUY_URL, seat)
        self.assertNotIn(AUTOPSY, wire)
        self.assertNotIn(AUTOPSY, seat)

    def test_prior_seat_carriers_were_not_reminted(self) -> None:
        self.assertTrue(GROK_SEAT_01.is_file())
        self.assertTrue(ACTION.is_file())
        grok = GROK_SEAT_01.read_text(encoding="utf-8")
        action = ACTION.read_text(encoding="utf-8")
        orig = ORIG.read_text(encoding="utf-8")
        self.assertIn("id: grok-seat-carry-work-20260919-01", grok)
        self.assertIn("id: action-20260919040904-a4550c3af759", action)
        self.assertIn("NOT_MINTED", orig)
        self.assertIn("id: grok-seat-carry-work-20260919-02", GROK_SEAT_02.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
