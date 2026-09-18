#!/usr/bin/env python3
"""Hermetic: mcp-conformance.html buy-path uses the existing Payment Links."""
from __future__ import annotations

import json
import re
import unittest
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

import test_checkout_landing_integrity as cli

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "mcp-conformance.html"
CATALOG = ROOT / "revenue/outcome_commerce/catalog.json"
SNAPSHOT = ROOT / "revenue/checkout_capability/snapshot.json"
CLAIM = "goat-mcp-conformance-checkout-wire-20260917-01"
RECEIPT_RUN = "https://buy.stripe.com/fZudR8bgV637fT3ctc43S0r"
SAME_DAY = "https://buy.stripe.com/14AeVcgBf2QV5epbp843S0s"
CHECKOUT_URLS = {
    "mcp-conformance-receipt-run": RECEIPT_RUN,
    "mcp-conformance-same-day-repair": SAME_DAY,
}
PLINKS = {
    "mcp-conformance-receipt-run": "plink_1UEGWVATH4EDE7XDNPUXHid5",
    "mcp-conformance-same-day-repair": "plink_1UEGWqATH4EDE7XDatjbiRHb",
}
SIBLING_RAILS = {
    "dealer-service-lead-rescue.html": "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "referral-intake-completeness.html": "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "repair-booking-preflight.html": "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "plant-downtime-handoff.html": "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
}


class GoatMcpConformanceCheckoutWire(unittest.TestCase):
    def test_door_and_catalog_carry_the_verified_payment_links(self) -> None:
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn(RECEIPT_RUN, html)
        self.assertIn(SAME_DAY, html)
        self.assertIn("Start the $49 receipt run", html)
        self.assertIn("Start the $250 same-day repair", html)
        self.assertIn("<noscript>", html)
        noscript = html.split("<noscript>", 1)[1].split("</noscript>", 1)[0]
        self.assertIn(RECEIPT_RUN, noscript)
        self.assertIn(SAME_DAY, noscript)
        self.assertNotIn('class="js-checkout-slot"', html)
        self.assertNotIn("pay.js", html)
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

        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        for sku, url in CHECKOUT_URLS.items():
            listing = next(row for row in catalog["listings"] if row.get("id") == sku)
            self.assertEqual(listing["checkout"]["url"], url)
            self.assertEqual(listing["checkout"]["status"], "ACTIVE_CHARGEABLE")
            funnel = catalog["funnels"][sku]
            self.assertEqual(funnel["readiness"], "READY_FOR_CHECKOUT")
            self.assertEqual(funnel["qualification"]["route"], "mcp-conformance.html")
            rail = next(row for row in snapshot["canonical_rails"] if row.get("sku") == sku)
            self.assertEqual(rail["url"], url)
            self.assertEqual(rail["plink"], PLINKS[sku])
            self.assertTrue(rail["livemode"])
            self.assertEqual(rail["exposure"], "CHECKOUT_FIRST")
        self.assertEqual(cli.landing_surface_errors(ROOT), [])

    def test_autopsy_and_199_sibling_doors_keep_their_existing_rails(self) -> None:
        page = PAGE.read_text(encoding="utf-8")
        for route, url in SIBLING_RAILS.items():
            with self.subTest(route=route):
                text = (ROOT / route).read_text(encoding="utf-8")
                self.assertIn(url, text)
                self.assertNotIn(RECEIPT_RUN, text)
                self.assertNotIn(SAME_DAY, text)
                self.assertNotIn(url, page)
        self.assertTrue((ROOT / "p" / f"{CLAIM}.md").is_file())


if __name__ == "__main__":
    unittest.main()
