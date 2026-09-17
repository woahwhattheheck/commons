#!/usr/bin/env python3
"""Hermetic: agent-ops.html buy-path uses existing rails without promoting stale chargeability."""
from __future__ import annotations

import json
import re
import unittest
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

import test_checkout_landing_integrity as cli

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "agent-ops.html"
SCRIPT = ROOT / "agent-ops.js"
CHECKOUT = ROOT / "agent-ops-checkout.json"
SHELF = ROOT / "revenue/checkout_capability/offer-shelf-links-20260910.json"
CLAIM = "goat-agent-ops-checkout-wire-20260917-01"
OPERATOR = "https://buy.stripe.com/7sYdR8bgVezD8qBgJs43S0u"
FOUNDRY = "https://buy.stripe.com/4gMcN4gBffDH8qBfFo43S0v"
CHECKOUT_URLS = {
    "operator": OPERATOR,
    "foundry": FOUNDRY,
}
PLINKS = {
    "operator": "plink_1UEGXbATH4EDE7XDMPcqDIPA",
    "foundry": "plink_1UEGXwATH4EDE7XDnnuCSG66",
}
SHELF_KEYS = {
    "operator": "commons-agent-ops-operator",
    "foundry": "commons-agent-ops-foundry",
}
SIBLING_RAILS = {
    "agent-rescue.html": "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
    "dealer-service-lead-rescue.html": "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "referral-intake-completeness.html": "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "repair-booking-preflight.html": "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "plant-downtime-handoff.html": "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
}
CTA_IDS = ("hero-pilot-cta", "operator-cta", "foundry-cta")


class GoatAgentOpsCheckoutWire(unittest.TestCase):
    def test_door_carries_verified_payment_links_without_static_currentness_claim(self) -> None:
        html = PAGE.read_text(encoding="utf-8")
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(OPERATOR, html)
        self.assertIn(FOUNDRY, html)
        self.assertIn("Buy Operator — $49/mo", html)
        self.assertIn("Buy Foundry — $2,500", html)
        self.assertIn("Buy Foundry pilot — $2,500", html)
        self.assertIn("checked-in Stripe route", html)
        self.assertIn("live chargeability", html)
        self.assertNotIn("reading checkout state", html)
        self.assertNotIn("live state loading", html)
        self.assertNotIn("2 provider-verified checkout routes are active", html)
        self.assertNotIn("current live chargeability is confirmed", html)
        self.assertIn("does not live-query Stripe", html)
        self.assertIn("checked-in snapshot", script)
        self.assertIn("does not live-query Stripe", script)
        self.assertNotIn("provider-verified checkout route", script)
        self.assertIn("<noscript>", html)
        noscript = html.split("<noscript>", 1)[1].split("</noscript>", 1)[0]
        self.assertIn(OPERATOR, noscript)
        self.assertIn(FOUNDRY, noscript)
        self.assertIn("current provider chargeability cannot be confirmed", noscript)
        self.assertNotIn('class="js-checkout-slot"', html)
        self.assertNotIn("pay.js", html)
        for cta_id in CTA_IDS:
            self.assertIn(f'id="{cta_id}"', html)
        self.assertIn("mailto:tokenjunkielabs@gmail.com?subject=Commons%20Agent%20Ops%20Operator", html)
        self.assertIn("mailto:tokenjunkielabs@gmail.com?subject=Commons%20Agent%20Ops%20Foundry", html)
        self.assertIn("mailto:tokenjunkielabs@gmail.com?subject=Commons%20Agent%20Ops%20pilot", html)
        self.assertIn('id="live-cash"', html)
        self.assertIn("./agent-rescue.html", html)
        self.assertIn("checkoutPresentation", script)
        self.assertNotIn("STATIC_CHARGEABLE", script)
        self.assertIn("primary CTAs were demoted to contact-only", script)
        self.assertIn("current chargeability is unconfirmed", script)
        hrefs = [
            unescape(value)
            for value in re.findall(r'href="(https://buy\.stripe\.com/[^"]+)"', html)
        ]
        self.assertGreaterEqual(len(hrefs), 4)
        allowed = set(CHECKOUT_URLS.values())
        seen = set()
        for href in hrefs:
            parsed = urlsplit(href)
            rail = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            self.assertIn(rail, allowed)
            self.assertEqual(parsed.query, "")
            seen.add(rail)
        self.assertEqual(seen, allowed)

        checkout = json.loads(CHECKOUT.read_text(encoding="utf-8"))
        shelf = json.loads(SHELF.read_text(encoding="utf-8"))
        for sku, url in CHECKOUT_URLS.items():
            offer = checkout["offers"][sku]
            recorded = shelf["links"][SHELF_KEYS[sku]]
            self.assertEqual(offer["link"]["url"], url)
            self.assertEqual(offer["link"]["status"], "ACTIVE")
            self.assertTrue(offer["link"]["active"])
            self.assertEqual(offer["link"]["payment_link_id"], PLINKS[sku])
            self.assertEqual(recorded["url"], url)
            self.assertEqual(recorded["payment_link_id"], PLINKS[sku])
            self.assertTrue(recorded["livemode"])
            self.assertTrue(recorded["active"])
            self.assertEqual(recorded["product_page"], "agent-ops.html")
        self.assertEqual(cli.landing_surface_errors(ROOT), [])

    def test_autopsy_and_199_sibling_doors_keep_their_existing_rails(self) -> None:
        page = PAGE.read_text(encoding="utf-8")
        for route, url in SIBLING_RAILS.items():
            with self.subTest(route=route):
                text = (ROOT / route).read_text(encoding="utf-8")
                self.assertIn(url, text)
                self.assertNotIn(OPERATOR, text)
                self.assertNotIn(FOUNDRY, text)
                self.assertNotIn(url, page)
        self.assertTrue((ROOT / "p" / f"{CLAIM}.md").is_file())


if __name__ == "__main__":
    unittest.main()
