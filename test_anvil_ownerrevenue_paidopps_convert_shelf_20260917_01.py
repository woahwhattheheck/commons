#!/usr/bin/env python3
"""anvil-ownerrevenue-paidopps-convert-shelf-20260917-01 — convert shelves.

Wire the EXISTING live White Box hour $250 Stripe Payment Link as a
first-screen Buy CTA on owner-now-revenue.html. Do not invent new
buy.stripe.com host paths. Keep Live cash product-page links.
Character-exact twin of the shipped thin shelf. Tip KEEP.
paid-opportunities.html already carries the twin shelf via
swe2max-paidopps-rightnow-convert-shelf-20260917-01 — presence-checked
only, left exactly as shipped.
Hands off demand-survive/first-night, open-door/interconnect,
observatory/tabletop, writing/cweather, dj-trail/hub-eyes,
visual/titanmcp, ringdelta/swarm-dc, hub_pages, ingest, fat index,
#8802, commercial.html, diagnostic.html. Static doors — no hub remint.
337 NO. No Muse. Do not remint BRYCE ids.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OWNER_NOW = ROOT / "owner-now-revenue.html"
PAID_OPPS = ROOT / "paid-opportunities.html"
RECEIPT = ROOT / "p" / "anvil-ownerrevenue-paidopps-convert-shelf-20260917-01.md"

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
CLAIM = "anvil-ownerrevenue-paidopps-convert-shelf-20260917-01"
PAID_OPPS_CITE = "swe2max-paidopps-rightnow-convert-shelf-20260917-01"
HANDS_OFF = (
    "demand-survive.html",
    "first-night.html",
    "open-door.html",
    "interconnect.html",
    "observatory.html",
    "tabletop.html",
    "writing.html",
    "cweather.html",
    "dj-trail.html",
    "hub-eyes.html",
    "visual.html",
    "titanmcp.html",
    "ringdelta.html",
    "swarm-dc.html",
)
AVATARS_CITE = "type-avatars-clans-convert-shelf-20260917-01"
GOAT_CITE = "goat-tips-live-cash-doors-20260905-01"
FORGE_CITE = "forge-commerce-diagnostic-tip-shelf-20260905-01"
ANVIL_PRIOR = "anvil-opendoor-interconnect-convert-shelf-20260917-01"


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


class TestAnvilOwnerrevenuePaidoppsConvertShelf2026091701(unittest.TestCase):
    def test_owner_now_reuses_exactly_the_existing_live_buy(self) -> None:
        html = OWNER_NOW.read_text(encoding="utf-8")
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
        self.assertIn("OWNER_NOW — generate revenue", html)
        self.assertIn("ground/OWNER_NOW.md", html)
        self.assertIn("owner_now_revenue.py", html)
        self.assertIn('id="rail-failover"', html)
        self.assertIn("pay.js?v=20260902b", html)
        self.assertIn("A click is intent, not cash", html)
        self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
        self.assertNotIn("live Stripe URLs", html)
        self.assertNotIn(">Pay ", html)
        self.assertNotIn("337 NO", html)

    def test_paid_opportunities_twin_shelf_present(self) -> None:
        html = PAID_OPPS.read_text(encoding="utf-8")
        self.assertIn('id="buy-now-live-checkout"', html)
        self.assertIn("Buy now — live checkout", html)
        self.assertIn('class="cta"', html)
        self.assertIn("data-checkout", html)
        found = live_buy_urls(html)
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        self.assertNotIn("donate.stripe.com", html)
        shelf = convert_shelf(html)
        for label in BUY_LABELS:
            self.assertIn(label, shelf, label)
        self.assertIn(PAID_OPPS_CITE, shelf)
        self.assertEqual(html.count('id="buy-now-live-checkout"'), 1)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: anvil-ownerrevenue-paidopps-convert-shelf-20260917-01", text)
        self.assertIn(CLAIM, text)
        self.assertIn(AVATARS_CITE, text)
        self.assertIn(GOAT_CITE, text)
        self.assertIn(FORGE_CITE, text)
        self.assertIn(ANVIL_PRIOR, text)
        self.assertIn(PAID_OPPS_CITE, text)
        self.assertIn("Do not remint BRYCE ids", text)
        self.assertNotIn("id: BRYCE-", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "owner-now-revenue.html",
            "paid-opportunities.html",
            "avatars.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertIn(name, text)
        for name in HANDS_OFF:
            self.assertTrue((ROOT / name).is_file(), name)
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
