#!/usr/bin/env python3
"""Hermetic: titan-hour.html buy-path uses the existing White Box-hour Payment Link."""
from __future__ import annotations

import json
import re
import unittest
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

import test_checkout_landing_integrity as cli

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "titan-hour.html"
CATALOG = ROOT / "revenue/outcome_commerce/catalog.json"
SNAPSHOT = ROOT / "revenue/checkout_capability/snapshot.json"
SKU_CARD = ROOT / "land/sku-whitebox-hour-20260826.md"
CLAIM = "goat-titan-hour-checkout-wire-20260917-01"
SKU = "sku-whitebox-hour-20260826"
CHECKOUT_URL = "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07"
PLINK = "plink_1U8lgGATH4EDE7XDlrVYTWhu"
SIBLING_RAILS = {
    "dealer-service-lead-rescue.html": "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "referral-intake-completeness.html": "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "repair-booking-preflight.html": "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "plant-downtime-handoff.html": "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
}


class GoatTitanHourCheckoutWire(unittest.TestCase):
    def test_door_and_catalog_carry_the_verified_payment_link(self) -> None:
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn(CHECKOUT_URL, html)
        self.assertIn("Buy White Box hour — $250", html)
        self.assertGreaterEqual(html.count("Buy White Box hour — $250"), 2)
        self.assertIn("<noscript>", html)
        noscript = html.split("<noscript>", 1)[1].split("</noscript>", 1)[0]
        self.assertIn(CHECKOUT_URL, noscript)
        self.assertNotIn("Loading verified White Box-hour purchase route", html)
        self.assertIn('class="js-checkout-slot"', html)
        self.assertIn('data-sku="sku-whitebox-hour-20260826"', html)
        self.assertIn('src="./pay.js?v=20260902a"', html)
        self.assertIn('id="intake"', html)
        self.assertIn("./commerce.html#sku-whitebox-hour-20260826", html)
        hrefs = [
            unescape(value)
            for value in re.findall(r'href="(https://buy\.stripe\.com/[^"]+)"', html)
        ]
        self.assertGreaterEqual(len(hrefs), 3)
        for href in hrefs:
            parsed = urlsplit(href)
            self.assertEqual(
                f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                CHECKOUT_URL,
            )
            self.assertEqual(parsed.query, "")

        sku_card = SKU_CARD.read_text(encoding="utf-8")
        self.assertIn(CHECKOUT_URL, sku_card)
        self.assertIn(PLINK, sku_card)

        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        listing = next(row for row in catalog["listings"] if row.get("id") == SKU)
        self.assertEqual(listing["checkout"]["url"], CHECKOUT_URL)
        self.assertEqual(listing["checkout"]["status"], "ACTIVE_CHARGEABLE")
        funnel = catalog["funnels"][SKU]
        self.assertEqual(funnel["readiness"], "READY_FOR_QUALIFICATION")
        self.assertEqual(
            funnel["qualification"]["route"],
            "commerce.html#sku-whitebox-hour-20260826",
        )

        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        rail = next(row for row in snapshot["canonical_rails"] if row.get("sku") == SKU)
        self.assertEqual(rail["url"], CHECKOUT_URL)
        self.assertEqual(rail["plink"], PLINK)
        self.assertTrue(rail["livemode"])
        self.assertEqual(rail["exposure"], "INTAKE_FIRST")
        self.assertEqual(cli.landing_surface_errors(ROOT), [])

    def test_autopsy_and_199_sibling_doors_keep_their_existing_rails(self) -> None:
        page = PAGE.read_text(encoding="utf-8")
        for route, url in SIBLING_RAILS.items():
            with self.subTest(route=route):
                text = (ROOT / route).read_text(encoding="utf-8")
                self.assertIn(url, text)
                self.assertNotIn(CHECKOUT_URL, text)
                self.assertNotIn(url, page)
        self.assertTrue((ROOT / "p" / f"{CLAIM}.md").is_file())


if __name__ == "__main__":
    unittest.main()
