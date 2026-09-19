#!/usr/bin/env python3
"""type-resources-catalog-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Link URLs onto resources.html and
catalog.html. Do not invent new buy.stripe.com host paths. Tip KEEP
relative doors stay. Hands off tips.html, pay.html, tools-cash.html,
bazaar.html, commerce.html, commercial.html, diagnostic.html,
ground/*.md Larger KEEP, Latch pack, Quill product doors, Goat
agent-ops, and #8802.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESOURCES = ROOT / "resources.html"
CATALOG = ROOT / "catalog.html"
RECEIPT = ROOT / "p" / "type-resources-catalog-convert-shelf-20260917-01.md"

ALLOWED_LIVE_BUY_URLS = frozenset(
    {
        "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
        "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
        "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
        "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
        "https://buy.stripe.com/7sYdR8ckZgHLbCN50K43S0y",
        "https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x",
        "https://buy.stripe.com/28E9AS70F6378qB2SC43S0w",
        "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
    }
)
BUY_HOST_PATH = re.compile(
    r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
SHELF_LABELS = (
    ("Dealer Service Lead Rescue", "$199"),
    ("Referral Intake Completeness", "$199"),
    ("Repair Booking Preflight", "$199"),
    ("Plant Downtime Handoff", "$199"),
    ("Hotel room-turn", "$2,500"),
    ("Late-cancel / no-show", "$3,500"),
    ("Chargeback Evidence Readiness", "$4,000"),
    ("White Box hour", "$250"),
)
RELATIVE_DOORS = (
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
    "./hotel-room-turn-evidence.html",
    "./late-cancel-noshow-fee-leakage.html",
    "./chargeback-evidence-readiness.html",
    "./diagnostic.html",
    "./commercial.html",
)
PAGES = (RESOURCES, CATALOG)


def live_buy_urls(html: str) -> set[str]:
    """Canonical https://buy.stripe.com/<path> identities found in HTML."""
    return {
        f"https://buy.stripe.com/{path}"
        for path in BUY_HOST_PATH.findall(html)
    }


def convert_shelf(html: str) -> str:
    """First-screen Buy now shelf, cut before live-cash / next landmark."""
    after = html.split('id="buy-now-live-checkout"', 1)[1]
    for marker in ('id="live-cash"', 'id="digit-note"', "<h2"):
        if marker in after:
            after = after.split(marker, 1)[0]
            break
    return after


class TestTypeResourcesCatalogConvertShelf2026091701(unittest.TestCase):
    def test_both_html_files_reuse_exactly_the_existing_live_buys(self) -> None:
        for page in PAGES:
            with self.subTest(page=page.name):
                html = page.read_text(encoding="utf-8")
                self.assertIn('id="buy-now-live-checkout"', html)
                self.assertIn("Buy now — live checkout", html)
                found = live_buy_urls(html)
                self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
                self.assertNotIn("donate.stripe.com", html)
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertIn(url, html)
                shelf = convert_shelf(html)
                h1_at = html.find("<h1")
                shelf_at = html.find('id="buy-now-live-checkout"')
                live_cash_at = html.find('id="live-cash"')
                self.assertGreater(h1_at, -1)
                self.assertGreater(shelf_at, h1_at)
                self.assertGreater(live_cash_at, shelf_at)
                for name, amount in SHELF_LABELS:
                    self.assertIn(name, shelf, name)
                    self.assertIn(amount, shelf, amount)
                for door in RELATIVE_DOORS:
                    self.assertIn(door, html, door)
                self.assertIn('id="live-cash"', html)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: type-resources-catalog-convert-shelf-20260917-01", text)
        self.assertIn("type-resources-catalog-convert-shelf-20260917-01", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "dealer-service-lead-rescue.html",
            "referral-intake-completeness.html",
            "repair-booking-preflight.html",
            "plant-downtime-handoff.html",
            "hotel-room-turn-evidence.html",
            "late-cancel-noshow-fee-leakage.html",
            "chargeback-evidence-readiness.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
