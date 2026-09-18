#!/usr/bin/env python3
"""wire-opportunity-claims-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
opportunity.html and claims.html. Do not invent new buy.stripe.com host
paths. Keep Live cash product-page links. Match tools.html /
commercial.html CTA style. Tip KEEP. Hands off Type commerce-agents/
offer/scope/business-packs, Latch pack, Goat tips/owner-now/titan-hour,
Quill salesforce/open-model, Wire tools/toolbench, ingest, fat index,
#8802.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host import opportunity_registry as opportunity_registry_mod


OPPORTUNITY = ROOT / "opportunity.html"
CLAIMS = ROOT / "claims.html"
RECEIPT = ROOT / "p" / "wire-opportunity-claims-convert-shelf-20260917-01.md"
RENDERER = ROOT / "host" / "opportunity_registry.py"

ALLOWED_LIVE_BUY_URLS = frozenset(
    {
        "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
    }
)
BUY_HOST_PATH = re.compile(
    r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
BUY_LABELS = ("Buy one White Box hour $250",)
LIVE_CASH_DOORS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
PAGES = (OPPORTUNITY, CLAIMS)


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


class TestWireOpportunityClaimsConvertShelf2026091701(unittest.TestCase):
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

    def test_opportunity_renderer_emits_the_same_existing_buys(self) -> None:
        source = RENDERER.read_text(encoding="utf-8")
        self.assertIn('id="buy-now-live-checkout"', source)
        self.assertNotIn("Buy Autopsy $29", source)
        self.assertIn("Buy one White Box hour $250", source)
        found = live_buy_urls(source)
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        live_cash = source.split('id="live-cash"', 1)[1]
        live_cash = live_cash.split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", live_cash)
        registry = json.loads(
            (ROOT / "revenue/ip/opportunity_registry.json").read_text(encoding="utf-8")
        )
        rendered = opportunity_registry_mod.render_opportunity_html(registry)
        self.assertEqual(live_buy_urls(rendered), ALLOWED_LIVE_BUY_URLS)
        self.assertNotIn("Buy Autopsy $29", rendered)
        self.assertIn("Buy one White Box hour $250", rendered)
        gen_cash = rendered.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", gen_cash)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: wire-opportunity-claims-convert-shelf-20260917-01", text)
        self.assertIn("wire-opportunity-claims-convert-shelf-20260917-01", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "opportunity.html",
            "claims.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
