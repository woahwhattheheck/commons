#!/usr/bin/env python3
"""type-pay-convert-shelf-existing-links-20260917-01 — pay.html convert shelf.

Wire EXISTING live Stripe Payment Link URLs onto pay.html. Do not invent
new buy.stripe.com host paths. Tip KEEP relative doors stay. Hands off
ground/*.md Larger KEEP and #8802.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PAY = ROOT / "pay.html"
RECEIPT = ROOT / "p" / "type-pay-convert-shelf-existing-links-20260917-01.md"

ALLOWED_LIVE_BUY_URLS = frozenset(
    {
        "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
        "https://buy.stripe.com/28E9AS70F6378qB2SC43S0w",
        "https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x",
        "https://buy.stripe.com/7sYdR8ckZgHLbCN50K43S0y",
    }
)
BUY_HOST_PATH = re.compile(
    r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
SHELF_LABELS = (
    ("Plant Downtime Handoff", "$199"),
    ("Chargeback Evidence Readiness", "$4,000"),
    ("Late-cancel / no-show", "$3,500"),
    ("Hotel room-turn", "$2,500"),
)
RELATIVE_DOORS = (
    "./plant-downtime-handoff.html",
    "./chargeback-evidence-readiness.html",
    "./late-cancel-noshow-fee-leakage.html",
    "./hotel-room-turn-evidence.html",
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
)


def live_buy_urls(html: str) -> set[str]:
    """Canonical https://buy.stripe.com/<path> identities found in HTML."""
    return {
        f"https://buy.stripe.com/{path}"
        for path in BUY_HOST_PATH.findall(html)
    }


class TestTypePayConvertShelfExistingLinks2026091701(unittest.TestCase):
    def test_pay_html_convert_shelf_reuses_exactly_five_existing_buys(self) -> None:
        html = PAY.read_text(encoding="utf-8")
        self.assertIn('id="buy-now-live-checkout"', html)
        self.assertIn("Buy now — live checkout", html)
        shelf = html.split('id="buy-now-live-checkout"', 1)[1].split(
            'id="owner-action"', 1
        )[0]
        found = live_buy_urls(shelf)
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        self.assertNotIn("donate.stripe.com", shelf)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, shelf)
            self.assertIn(url, html)
        for name, amount in SHELF_LABELS:
            self.assertIn(name, shelf, name)
            self.assertIn(amount, shelf, amount)
        for door in RELATIVE_DOORS:
            self.assertIn(door, html, door)
        self.assertIn('id="tip-shelf-199"', html)
        self.assertIn("Live tip-shelf diagnostics — $199 once each.", html)
        self.assertIn("Static HTML keeps Stripe URLs inert.", html)
        self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
        self.assertNotIn("live Stripe URLs", html)
        self.assertNotIn(">Pay ", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: type-pay-convert-shelf-existing-links-20260917-01", text)
        self.assertIn("type-pay-convert-shelf-existing-links-20260917-01", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "commercial.html",
            "plant-downtime-handoff.html",
            "chargeback-evidence-readiness.html",
            "late-cancel-noshow-fee-leakage.html",
            "hotel-room-turn-evidence.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
