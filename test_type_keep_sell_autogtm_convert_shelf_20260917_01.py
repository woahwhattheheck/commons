#!/usr/bin/env python3
"""type-keep-sell-autogtm-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
keep-sell.html and autogtm.html. Thin shelf only: Autopsy $29 and
White Box hour $250. Do not invent new buy.stripe.com host paths.
Do not wire the nine-link shelf. Keep Live cash product-page links.
Match live.html / avatars.html thin CTA style. Tip KEEP. Hands off
Wire Muse+arbitrage/attested-inference, Latch annex/archive, Goat
free-sample/humans/attested-runs/distribution, Quill wake/world,
Type action/capabilities/avatars/clans/commands/cloud-current,
MCP doors, Muse, lead spam, PUT ingest, fat index, #8802.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
KEEP_SELL = ROOT / "keep-sell.html"
AUTOGTM = ROOT / "autogtm.html"
RECEIPT = ROOT / "p" / "type-keep-sell-autogtm-convert-shelf-20260917-01.md"

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
PAGES = (KEEP_SELL, AUTOGTM)
CITE = "type-keep-sell-autogtm-convert-shelf-20260917-01"
ABOVE_FOLD_MAX = 4500
NINE_LINK_EXCLUDED = (
    "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
    "https://buy.stripe.com/7sYdR8ckZgHLbCN50K43S0y",
    "https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x",
    "https://buy.stripe.com/28E9AS70F6378qB2SC43S0w",
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
    for marker in ('id="live-cash"', "<main", "<h1"):
        if marker in after:
            after = after.split(marker, 1)[0]
            break
    return after


def live_cash_slice(html: str) -> str:
    after = html.split('id="live-cash"', 1)[1]
    if "</section>" in after:
        return after.split("</section>", 1)[0]
    return after


class TestTypeKeepSellAutogtmConvertShelf2026091701(unittest.TestCase):
    def test_both_pages_reuse_exactly_the_existing_live_buys(self) -> None:
        for page in PAGES:
            with self.subTest(page=page.name):
                html = page.read_text(encoding="utf-8")
                self.assertIn('id="buy-now-live-checkout"', html)
                self.assertIn("Buy now — live checkout", html)
                self.assertIn("Buy now", html)
                self.assertIn('class="cta"', html)
                self.assertIn("data-checkout", html)
                found = live_buy_urls(html)
                self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
                self.assertNotIn("donate.stripe.com", html)
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertIn(url, html)
                    self.assertEqual(html.count(url), 1, url)
                for url in NINE_LINK_EXCLUDED:
                    self.assertNotIn(url, html, url)
                shelf = convert_shelf(html)
                for label in BUY_LABELS:
                    self.assertIn(label, shelf, label)
                self.assertIn(CITE, shelf)
                self.assertIn('id="live-cash"', html)
                self.assertNotIn("buy.stripe.com", live_cash_slice(html))
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
                self.assertLess(
                    shelf_at,
                    ABOVE_FOLD_MAX,
                    f"{page.name} Buy shelf not above fold / first screen",
                )
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertLess(
                        html.find(url),
                        ABOVE_FOLD_MAX,
                        f"{page.name} {url} not above fold",
                    )
                for label in BUY_LABELS:
                    self.assertLess(
                        html.find(label),
                        ABOVE_FOLD_MAX,
                        f"{page.name} {label} not above fold",
                    )
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)
                self.assertIn(".cta{", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(f"id: {CITE}", text)
        self.assertIn(CITE, text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        self.assertNotIn("https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b", text)
        for name in (
            "keep-sell.html",
            "autogtm.html",
            "agent-rescue.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)
            self.assertIn(name, text)
        self.assertNotIn("arbitrage.html", text)
        self.assertNotIn("attested-inference.html", text)
        self.assertNotIn("annex.html", text)
        self.assertNotIn("free-sample.html", text)
        self.assertNotIn("wake.html", text)
        self.assertNotIn("action.html", text)
        self.assertNotIn("commands.html", text)
        self.assertNotIn("cloud-current.html", text)


if __name__ == "__main__":
    unittest.main()
