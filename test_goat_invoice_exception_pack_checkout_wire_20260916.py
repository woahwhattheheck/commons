#!/usr/bin/env python3
"""Hermetic: invoice-exception-pack $199 buy-path uses the existing Payment Link."""
from __future__ import annotations

import json
import re
import unittest
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

import test_checkout_landing_integrity as cli

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "invoice-exception-pack.html"
CATALOG = ROOT / "revenue/outcome_commerce/catalog.json"
SNAPSHOT = ROOT / "revenue/checkout_capability/snapshot.json"
CLAIM = "goat-invoice-exception-pack-checkout-wire-20260916-01"
CHECKOUT_URL = "https://buy.stripe.com/14A00i84Jdvz36hdxg43S0l"
PLINK = "plink_1UEGT5ATH4EDE7XDA7WFJthA"
SIBLING_RAILS = {
    "agent-rescue.html": "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
    "dealer-service-lead-rescue.html": "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "referral-intake-completeness.html": "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "repair-booking-preflight.html": "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "plant-downtime-handoff.html": "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
}


class GoatInvoiceExceptionPackCheckoutWire(unittest.TestCase):
    def test_door_and_catalog_carry_the_verified_payment_link(self) -> None:
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn(CHECKOUT_URL, html)
        self.assertIn("Start the $199 diagnostic", html)
        self.assertIn("<noscript>", html)
        noscript = html.split("<noscript>", 1)[1].split("</noscript>", 1)[0]
        self.assertIn(CHECKOUT_URL, noscript)
        self.assertNotIn('class="js-checkout-slot"', html)
        hrefs = [
            unescape(value)
            for value in re.findall(r'href="(https://buy\.stripe\.com/[^"]+)"', html)
        ]
        self.assertGreaterEqual(len(hrefs), 2)
        for href in hrefs:
            parsed = urlsplit(href)
            self.assertEqual(
                f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                CHECKOUT_URL,
            )
            self.assertEqual(parsed.query, "")

        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        listing = next(
            row for row in catalog["listings"] if row.get("id") == "invoice-exception-pack"
        )
        self.assertEqual(listing["checkout"]["url"], CHECKOUT_URL)
        self.assertEqual(listing["checkout"]["status"], "ACTIVE_CHARGEABLE")
        funnel = catalog["funnels"]["invoice-exception-pack"]
        self.assertEqual(funnel["readiness"], "READY_FOR_CHECKOUT")
        self.assertEqual(funnel["qualification"]["route"], "invoice-exception-pack.html")

        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        rail = next(
            row for row in snapshot["canonical_rails"] if row.get("sku") == "invoice-exception-pack"
        )
        self.assertEqual(rail["url"], CHECKOUT_URL)
        self.assertEqual(rail["plink"], PLINK)
        self.assertTrue(rail["livemode"])
        self.assertEqual(rail["exposure"], "CHECKOUT_FIRST")
        self.assertEqual(cli.landing_surface_errors(ROOT), [])

    def test_autopsy_and_199_sibling_doors_keep_their_existing_rails(self) -> None:
        invoice = PAGE.read_text(encoding="utf-8")
        for route, url in SIBLING_RAILS.items():
            with self.subTest(route=route):
                text = (ROOT / route).read_text(encoding="utf-8")
                self.assertIn(url, text)
                self.assertNotIn(CHECKOUT_URL, text)
                self.assertNotIn(url, invoice)
        self.assertTrue((ROOT / "p" / f"{CLAIM}.md").is_file())


if __name__ == "__main__":
    unittest.main()
