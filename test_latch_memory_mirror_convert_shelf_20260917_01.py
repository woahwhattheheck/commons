#!/usr/bin/env python3
"""latch-memory-mirror-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
memory.html and mirror.html. Do not invent new buy.stripe.com host
paths. Keep Live cash product-page links. Mirror start/ledger #15585
and reach/reply #15578 CTA structure. Tip KEEP. Hands off
start/ledger/embassy/glyphs/visual/titanmcp, hub_pages, ingest, fat
index, #8802, commercial.html, diagnostic.html. Static doors — no hub
remint. 337 NO. No Muse. Do not remint BRYCE ids.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MEMORY = ROOT / "memory.html"
MIRROR = ROOT / "mirror.html"
RECEIPT = ROOT / "p" / "latch-memory-mirror-convert-shelf-20260917-01.md"

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
PAGES = (MEMORY, MIRROR)
CLAIM = "latch-memory-mirror-convert-shelf-20260917-01"
HANDS_OFF = (
    "start.html",
    "ledger.html",
    "embassy.html",
    "glyphs.html",
    "visual.html",
    "titanmcp.html",
)
BRYCE_MIRROR_CITE = "BRYCE-1787050390335"


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


class TestLatchMemoryMirrorConvertShelf2026091701(unittest.TestCase):
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
                self.assertEqual(html.count('id="live-cash"'), 1)
                self.assertEqual(html.count('id="buy-now-live-checkout"'), 1)
                self.assertNotIn("tools-cash.html", html)
                self.assertIn("https://webmcp-pad.vercel.app/", html)
                self.assertIn("1.4.5", html)
                if page.name == "memory.html":
                    self.assertIn("home-bar", html)
                    self.assertIn('id="pad-open"', html)
                    self.assertIn("writing.html", html)
                    self.assertIn("WRITE-NOW", html)
                    self.assertIn("memory/{CLAIM}.html", html)
                    self.assertIn("never a posting gate", html)
                    self.assertNotIn("builds.html", html)
                else:
                    self.assertIn("home-bar", html)
                    self.assertIn(BRYCE_MIRROR_CITE, html)
                    self.assertIn("Optional capability context", html)
                    self.assertIn("https://ntfy.sh/woahwhattheheck-commons-board", html)
                    self.assertIn("does not actuate devices", html)
                    self.assertNotIn("337", html)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)
                self.assertNotIn("337 NO", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: latch-memory-mirror-convert-shelf-20260917-01", text)
        self.assertIn(CLAIM, text)
        self.assertIn(BRYCE_MIRROR_CITE, text)
        self.assertNotIn(f"id: {BRYCE_MIRROR_CITE}", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "memory.html",
            "mirror.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)
        for name in HANDS_OFF:
            self.assertTrue((ROOT / name).is_file(), name)
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
