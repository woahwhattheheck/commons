#!/usr/bin/env python3
"""latch-net159-wakeup-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
net159.html and wakeup.html. Do not invent new buy.stripe.com host
paths. Keep Live cash product-page links. Mirror start/ledger #15585
CTA structure. Tip KEEP. Hands off memory/mirror/embassy/glyphs/visual/
titanmcp, hub_pages, ingest, fat index, #8802, commercial.html,
diagnostic.html. Static doors — no hub remint. 337 NO. No Muse.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NET159 = ROOT / "net159.html"
WAKEUP = ROOT / "wakeup.html"
RECEIPT = ROOT / "p" / "latch-net159-wakeup-convert-shelf-20260917-01.md"

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
PAGES = (NET159, WAKEUP)
CLAIM = "latch-net159-wakeup-convert-shelf-20260917-01"
HANDS_OFF = (
    "memory.html",
    "mirror.html",
    "embassy.html",
    "glyphs.html",
    "visual.html",
    "titanmcp.html",
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


class TestLatchNet159WakeupConvertShelf2026091701(unittest.TestCase):
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
                self.assertEqual(html.count('id="live-cash"'), 1)
                self.assertEqual(html.count('id="buy-now-live-checkout"'), 1)
                self.assertIn("https://webmcp-pad.vercel.app/", html)
                self.assertIn("1.4.5", html)
                if page.name == "net159.html":
                    self.assertGreater(html.find("<h1"), -1)
                    self.assertIn("not a Commons", html)
                    self.assertIn("net159-dude", html)
                    self.assertIn("cairn-netlist-logic-analyser-20260820-03", html)
                    self.assertIn("./visual.html", html)
                    self.assertIn("look.css", html)
                else:
                    nav_at = html.find('class="nav"')
                    self.assertGreater(nav_at, -1)
                    self.assertGreater(titan_at, nav_at)
                    self.assertIn('id="digit-note"', html)
                    digit_at = html.find('id="digit-note"')
                    self.assertGreater(digit_at, shelf_at)
                    self.assertGreater(live_cash_at, digit_at)
                    self.assertIn("python host/muhl_tools_once.py --go", html)
                    self.assertIn("https://commons-spark-mcp.vercel.app/mcp", html)
                    self.assertIn("latch-wake-super-mcp-pointer-20260902-01", html)
                    self.assertIn("./wire.html", html)
                    self.assertIn("Do not smash commons.mno", html)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)
                self.assertNotIn("337 NO", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: latch-net159-wakeup-convert-shelf-20260917-01", text)
        self.assertIn(CLAIM, text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "net159.html",
            "wakeup.html",
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
