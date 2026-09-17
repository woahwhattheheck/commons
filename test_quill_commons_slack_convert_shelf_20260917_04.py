#!/usr/bin/env python3
"""quill-commons-slack-convert-shelf-20260917-04 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
commons-slack.html and commons-slack-chunk.html. Do not invent new buy.stripe.com
host paths. Keep Live cash product-page links. Match Quill supermcp/telegram CTA style.
Tip KEEP. Hands off Type expertise/interconnect, Latch demand-survive/first-night,
Wire sell/X, Anvil open-door/interconnect, Goat tip shelves / owner-now-revenue,
Quill prior shelves including visual/titanmcp, ringdelta/swarm-dc, supermcp/telegram,
#8802, invent Stripe, lead spam. Muse NOT opened.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import hub_pages


ROOT = Path(__file__).resolve().parent
COMMONS_SLACK = ROOT / "commons-slack.html"
COMMONS_SLACK_CHUNK = ROOT / "commons-slack-chunk.html"
RECEIPT = ROOT / "p" / "quill-commons-slack-convert-shelf-20260917-04.md"
RENDERER = ROOT / "hub_pages.py"

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
PAGES = (COMMONS_SLACK, COMMONS_SLACK_CHUNK)
CLAIM = "quill-commons-slack-convert-shelf-20260917-04"


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


class TestQuillCommonsSlackConvertShelf2026091704(unittest.TestCase):
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
        self.assertIn("COMMONS_SLACK_CONVERT_SHELF_HTML", source)
        self.assertIn(
            'id="buy-now-live-checkout"',
            hub_pages.COMMONS_SLACK_CONVERT_SHELF_HTML,
        )
        self.assertIn(
            "Buy Autopsy $29", hub_pages.COMMONS_SLACK_CONVERT_SHELF_HTML
        )
        self.assertIn(
            "Buy one White Box hour $250",
            hub_pages.COMMONS_SLACK_CONVERT_SHELF_HTML,
        )
        self.assertIn(CLAIM, hub_pages.COMMONS_SLACK_CONVERT_SHELF_HTML)
        found = live_buy_urls(hub_pages.COMMONS_SLACK_CONVERT_SHELF_HTML)
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        self.assertNotIn("buy.stripe.com", hub_pages.LIVE_CASH_PRODUCTS_HTML)

    def test_receipt_names_the_claim_and_paths(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(CLAIM, text)
        self.assertIn("commons-slack.html", text)
        self.assertIn("commons-slack-chunk.html", text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("#8802 off", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)


if __name__ == "__main__":
    unittest.main()
