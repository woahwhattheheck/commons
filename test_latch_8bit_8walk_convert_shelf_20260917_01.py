#!/usr/bin/env python3
"""latch-8bit-8walk-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
8bit.html and 8walk.html. Do not invent new buy.stripe.com host paths.
Keep Live cash product-page links. Match annex.html / archive.html CTA
style (Latch #15529). Tip KEEP. Hands off Type payment-capability /
offer / scope, Wire tools/toolbench / entry/land, Latch annex/archive /
pack / fleet-work-order, commercial.html, diagnostic.html, ingest, fat
index, #8802. Static doors — no hub remint.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BIT = ROOT / "8bit.html"
WALK = ROOT / "8walk.html"
RECEIPT = ROOT / "p" / "latch-8bit-8walk-convert-shelf-20260917-01.md"

ALLOWED_LIVE_BUY_URLS = frozenset(
    {
        "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
    }
)
BUY_HOST_PATH = re.compile(
    r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
BUY_LABELS = (
    "Buy one White Box hour $250",
)
LIVE_CASH_DOORS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
PAGES = (BIT, WALK)
CLAIM = "latch-8bit-8walk-convert-shelf-20260917-01"


def live_buy_urls(html: str) -> set[str]:
    """Canonical https://buy.stripe.com/<path> identities found in HTML."""
    return {
        f"https://buy.stripe.com/{path}"
        for path in BUY_HOST_PATH.findall(html)
    }


def convert_shelf(html: str) -> str:
    """First-screen Buy now shelf, cut before live-cash."""
    after = html.split('id="buy-now-live-checkout"', 1)[1]
    for marker in ('id="live-cash"', "<main", "<h1"):
        if marker in after:
            after = after.split(marker, 1)[0]
            break
    return after


class TestLatch8bit8walkConvertShelf2026091701(unittest.TestCase):
    def test_both_pages_reuse_exactly_the_existing_live_buys(self) -> None:
        for page in PAGES:
            with self.subTest(page=page.name):
                html = page.read_text(encoding="utf-8")
                self.assertIn('id="buy-now-live-checkout"', html)
                self.assertIn("Buy now — live checkout", html)
                self.assertIn('class="cta"', html)
                self.assertIn("data-checkout", html)
                found = live_buy_urls(html)
                self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
                self.assertNotIn("donate.stripe.com", html)
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertIn(url, html)
                shelf = convert_shelf(html)
                for label in BUY_LABELS:
                    self.assertIn(label, shelf, label)
                self.assertIn(CLAIM, shelf)
                self.assertIn('id="live-cash"', html)
                live_cash = html.split('id="live-cash"', 1)[1]
                live_cash = live_cash.split("</section>", 1)[0]
                self.assertNotIn("buy.stripe.com", live_cash)
                for door in LIVE_CASH_DOORS:
                    self.assertIn(door, html, door)
                self.assertIn("Larger fixed engagements", html)
                self.assertIn("diagnostic.html", html)
                self.assertIn("commercial.html", html)
                nav_or_h1 = html.find("<h1")
                shelf_at = html.find('id="buy-now-live-checkout"')
                live_cash_at = html.find('id="live-cash"')
                self.assertGreater(nav_or_h1, -1)
                self.assertGreater(shelf_at, -1)
                self.assertGreater(live_cash_at, shelf_at)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: latch-8bit-8walk-convert-shelf-20260917-01", text)
        self.assertIn(CLAIM, text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "8bit.html",
            "8walk.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
