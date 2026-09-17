#!/usr/bin/env python3
"""latch-demand-survive-first-night-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
demand-survive.html and first-night.html. Do not invent new buy.stripe.com
host paths. Keep Live cash product-page links. Mirror dj-trail/hub-eyes
and writing/cweather CTA structure. Tip KEEP. Hands off plug/wire/
observatory/tabletop/visual/titanmcp/insights/swarm-dc/ringdelta/
open-door/interconnect/right-now, hub_pages, ingest, fat index, #8802,
commercial.html, diagnostic.html. Static doors — no hub remint. 337 NO.
No Muse. Do not remint BRYCE ids.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEMAND = ROOT / "demand-survive.html"
FIRST_NIGHT = ROOT / "first-night.html"
RECEIPT = ROOT / "p" / "latch-demand-survive-first-night-convert-shelf-20260917-01.md"

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
PAGES = (DEMAND, FIRST_NIGHT)
CLAIM = "latch-demand-survive-first-night-convert-shelf-20260917-01"
HANDS_OFF = (
    "plug.html",
    "wire.html",
    "observatory.html",
    "tabletop.html",
    "visual.html",
    "titanmcp.html",
    "insights.html",
    "swarm-dc.html",
    "ringdelta.html",
    "open-door.html",
    "interconnect.html",
    "right-now.html",
)
DJ_TRAIL_CITE = "latch-dj-trail-hub-eyes-convert-shelf-20260917-01"
WRITING_CITE = "latch-writing-cweather-convert-shelf-20260917-01"
BRYCE_FIRST_NIGHT = "p/BRYCE-1787055115124-bwepj0.html"


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


class TestLatchDemandSurviveFirstNightConvertShelf2026091701(unittest.TestCase):
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
                if page.name == "demand-survive.html":
                    self.assertIn("Commons demand survive", html)
                    self.assertIn("occupancy.md", html)
                    self.assertIn("current-work.html", html)
                    self.assertIn("demand_survive.py", html)
                    self.assertIn("ground/DEMANDS.json", html)
                    self.assertIn("Astra D5", html)
                    self.assertIn("quill-d5-demand-survive-20260904-01", html)
                    self.assertIn("No JavaScript needed", html)
                    self.assertNotIn("337", html)
                else:
                    self.assertIn("The First Night", html)
                    self.assertIn("books.html", html)
                    self.assertIn("to/FABLE.html", html)
                    self.assertIn("relay-the-first-night-20260818-253", html)
                    self.assertIn(BRYCE_FIRST_NIGHT, html)
                    self.assertIn("THE FIRST NIGHT — chapter one", html)
                    self.assertIn("Small book page", html)
                    self.assertIn("Here ends part one", html)
                    self.assertNotIn("login", html.lower())
                    self.assertNotIn("337", html)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)
                self.assertNotIn("337 NO", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: latch-demand-survive-first-night-convert-shelf-20260917-01", text)
        self.assertIn(CLAIM, text)
        self.assertIn(DJ_TRAIL_CITE, text)
        self.assertIn(WRITING_CITE, text)
        self.assertIn("Do not remint BRYCE ids", text)
        self.assertNotIn("id: BRYCE-", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "demand-survive.html",
            "first-night.html",
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
