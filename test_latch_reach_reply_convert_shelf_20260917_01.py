#!/usr/bin/env python3
"""latch-reach-reply-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
reach.html and reply.html. Do not invent new buy.stripe.com host paths.
Keep Live cash product-page links. Match names.html / owner.html CTA
style (Latch #15574). Tip KEEP. Hands off hub_pages / ingest / fat
index / #8802 / commercial.html / diagnostic.html / trust.html /
topics.html / plug.html / wire.html / shots.html / start.html.
Static doors — no hub remint. 337 NO.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REACH = ROOT / "reach.html"
REPLY = ROOT / "reply.html"
RECEIPT = ROOT / "p" / "latch-reach-reply-convert-shelf-20260917-01.md"

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
PAGES = (REACH, REPLY)
CLAIM = "latch-reach-reply-convert-shelf-20260917-01"
HANDS_OFF = (
    "trust.html",
    "topics.html",
    "plug.html",
    "wire.html",
    "shots.html",
    "start.html",
)


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


class TestLatchReachReplyConvertShelf2026091701(unittest.TestCase):
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
                titan_at = html.find('id="titanmcp-pad-pointer"')
                shelf_at = html.find('id="buy-now-live-checkout"')
                live_cash_at = html.find('id="live-cash"')
                self.assertGreater(titan_at, -1)
                self.assertGreater(shelf_at, titan_at)
                self.assertGreater(live_cash_at, shelf_at)
                self.assertGreater(html.find("<h1"), -1)
                self.assertNotIn("tools-cash.html", html)
                if page.name == "reach.html":
                    self.assertIn('id="digit-note"', html)
                    self.assertIn("Reach hygiene callout", html)
                    self.assertIn('id="tools-board"', html)
                    self.assertIn("latch-wake-super-mcp-pointer-20260902-01", html)
                    self.assertIn("https://commons-spark-mcp.vercel.app/mcp", html)
                else:
                    self.assertIn("supersedes:", html)
                    self.assertIn('id="table-reply"', html)
                    self.assertIn("reply.js?v=20260824a", html)
                    self.assertNotIn("337", html)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)
                self.assertNotIn("337 NO", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: latch-reach-reply-convert-shelf-20260917-01", text)
        self.assertIn(CLAIM, text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "reach.html",
            "reply.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)
        for name in HANDS_OFF:
            self.assertTrue((ROOT / name).is_file(), name)
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
