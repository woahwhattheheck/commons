#!/usr/bin/env python3
"""quill-supermcp-telegram-convert-shelf-20260917-03 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
super-mcp.html and telegram.html. Do not invent new buy.stripe.com host paths.
Keep Live cash product-page links. Match Quill ringdelta/swarm-dc CTA style.
Tip KEEP. Hands off Type insights/grounding, Latch dj-trail/hub-eyes,
Wire sell/X, Anvil open-door/interconnect, Goat tip shelves, Quill prior
shelves including visual/titanmcp and ringdelta/swarm-dc, #8802, invent Stripe,
lead spam. Muse NOT opened.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import hub_pages


ROOT = Path(__file__).resolve().parent
SUPER_MCP = ROOT / "super-mcp.html"
TELEGRAM = ROOT / "telegram.html"
RECEIPT = ROOT / "p" / "quill-supermcp-telegram-convert-shelf-20260917-03.md"
RENDERER = ROOT / "hub_pages.py"

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
PAGES = (SUPER_MCP, TELEGRAM)
CLAIM = "quill-supermcp-telegram-convert-shelf-20260917-03"


def live_buy_urls(html: str) -> set[str]:
    return {
        f"https://buy.stripe.com/{path}"
        for path in BUY_HOST_PATH.findall(html)
    }


def convert_shelf(html: str) -> str:
    after = html.split('id="buy-now-live-checkout"', 1)[1]
    for marker in ('id="live-cash"', "<main", "<h1"):
        if marker in after:
            after = after.split(marker, 1)[0]
            break
    return after


class TestQuillSupermcpTelegramConvertShelf2026091703(unittest.TestCase):
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
                self.assertLess(shelf_at, nav_or_h1)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)

    def test_renderer_constants_document_the_same_existing_buys(self) -> None:
        source = RENDERER.read_text(encoding="utf-8")
        self.assertIn("SUPERMCP_TELEGRAM_CONVERT_SHELF_HTML", source)
        self.assertIn(
            'id="buy-now-live-checkout"',
            hub_pages.SUPERMCP_TELEGRAM_CONVERT_SHELF_HTML,
        )
        self.assertIn(
            "Buy one White Box hour $250",
            hub_pages.SUPERMCP_TELEGRAM_CONVERT_SHELF_HTML,
        )
        self.assertIn(CLAIM, hub_pages.SUPERMCP_TELEGRAM_CONVERT_SHELF_HTML)
        found = live_buy_urls(hub_pages.SUPERMCP_TELEGRAM_CONVERT_SHELF_HTML)
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        self.assertNotIn("buy.stripe.com", hub_pages.LIVE_CASH_PRODUCTS_HTML)

    def test_receipt_names_the_claim_and_paths(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(CLAIM, text)
        self.assertIn("super-mcp.html", text)
        self.assertIn("telegram.html", text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("#8802 off", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)


if __name__ == "__main__":
    unittest.main()
