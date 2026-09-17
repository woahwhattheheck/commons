#!/usr/bin/env python3
"""latch-writing-cweather-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
writing.html and cweather.html. Do not invent new buy.stripe.com host
paths. Keep Live cash product-page links. Mirror recents/subzero CTA
structure. Tip KEEP. Hands off command/coordination/visual/titanmcp/
flipbook/compress, hub_pages, ingest, fat index, #8802, commercial.html,
diagnostic.html. Static doors — no hub remint. 337 NO. No Muse.
Do not remint BRYCE ids.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WRITING = ROOT / "writing.html"
CWEATHER = ROOT / "cweather.html"
RECEIPT = ROOT / "p" / "latch-writing-cweather-convert-shelf-20260917-01.md"

ALLOWED_LIVE_BUY_URLS = frozenset(
    {
        "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
        "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
    }
)
BUY_HOST_PATH = re.compile(
    r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
BUY_LABELS = (
    "Buy Autopsy $29",
    "Buy one White Box hour $250",
)
LIVE_CASH_DOORS = (
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
PAGES = (WRITING, CWEATHER)
CLAIM = "latch-writing-cweather-convert-shelf-20260917-01"
HANDS_OFF = (
    "command.html",
    "coordination.html",
    "visual.html",
    "titanmcp.html",
    "flipbook.html",
    "compress.html",
)
WRITING_CITE = "goat-tips-live-cash-doors-20260905-01"
WRITING_FORGE = "forge-commerce-diagnostic-tip-shelf-20260905-01"
RECENTS_CITE = "latch-recents-subzero-convert-shelf-20260917-01"


def live_buy_urls(html: str) -> set[str]:
    """Canonical https://buy.stripe.com/<path> identities found in HTML."""
    return {
        f"https://buy.stripe.com/{path}"
        for path in BUY_HOST_PATH.findall(html)
    }


def convert_shelf(html: str) -> str:
    """First-screen Buy now shelf, cut before live-cash."""
    after = html.split('id="buy-now-live-checkout"', 1)[1]
    for marker in ('id="live-cash"', "<main"):
        if marker in after:
            after = after.split(marker, 1)[0]
            break
    return after


class TestLatchWritingCweatherConvertShelf2026091701(unittest.TestCase):
    def test_both_pages_reuse_exactly_the_existing_live_buys(self) -> None:
        for page in PAGES:
            with self.subTest(page=page.name):
                html = page.read_text(encoding="utf-8")
                self.assertIn('id="buy-now-live-checkout"', html)
                self.assertIn("Buy now — live checkout", html)
                self.assertIn('class="cta"', html)
                self.assertIn("data-checkout", html)
                self.assertIn(".cta{", html)
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
                titan_at = html.find('id="titanmcp-pad-pointer"')
                shelf_at = html.find('id="buy-now-live-checkout"')
                live_cash_at = html.find('id="live-cash"')
                self.assertGreater(titan_at, -1)
                self.assertGreater(shelf_at, titan_at)
                self.assertGreater(live_cash_at, shelf_at)
                self.assertGreater(html.find("<h1"), -1)
                self.assertEqual(len(re.findall(r'id="live-cash"(?!-)', html)), 1)
                self.assertEqual(html.count('id="buy-now-live-checkout"'), 1)
                self.assertIn("https://webmcp-pad.vercel.app/", html)
                self.assertIn("1.4.5", html)
                if page.name == "writing.html":
                    self.assertIn("Commons writing", html)
                    self.assertIn("WRITING.md", html)
                    self.assertIn('id="live-cash-doors"', html)
                    self.assertIn(WRITING_CITE, html)
                    self.assertIn(WRITING_FORGE, html)
                    self.assertIn("without embedding Stripe URLs", html)
                    doors = html.split('id="live-cash-doors"', 1)[1]
                    doors = doors.split("</section>", 1)[0]
                    self.assertNotIn("buy.stripe.com", doors)
                    self.assertNotIn("337", html)
                else:
                    self.assertIn("C — weather, not a score", html)
                    self.assertIn("look.css?v=20260820b", html)
                    self.assertIn("session.js?v=20260820y", html)
                    self.assertIn("cweather.js?v=20260820a", html)
                    self.assertIn("SEED0", html)
                    self.assertIn("4.49", html)
                    self.assertIn("44.20", html)
                    self.assertIn("two-rooms", html)
                    self.assertIn("compress.html", html)
                    self.assertNotIn("login", html.lower())
                    self.assertNotIn("337", html)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)
                self.assertNotIn("337 NO", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: latch-writing-cweather-convert-shelf-20260917-01", text)
        self.assertIn(CLAIM, text)
        self.assertIn(WRITING_CITE, text)
        self.assertIn(WRITING_FORGE, text)
        self.assertIn(RECENTS_CITE, text)
        self.assertIn("Do not remint BRYCE ids", text)
        self.assertNotIn("id: BRYCE-", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "writing.html",
            "cweather.html",
            "agent-rescue.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)
        for name in HANDS_OFF:
            self.assertTrue((ROOT / name).is_file(), name)
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
