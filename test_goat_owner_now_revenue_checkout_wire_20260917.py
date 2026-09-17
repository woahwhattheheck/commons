#!/usr/bin/env python3
"""Owner-now checkout identities stay exact while publication stays fail-closed."""
from __future__ import annotations

import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path

import test_checkout_landing_integrity as cli

ROOT = Path(__file__).resolve().parent


def _load_host(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "host" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checkout_capability = _load_host("checkout_capability")
payment_capability = _load_host("payment_capability")
PAGE = ROOT / "owner-now-revenue.html"
CATALOG = ROOT / "revenue/outcome_commerce/catalog.json"
SNAPSHOT = ROOT / "revenue/checkout_capability/snapshot.json"
CLAIM = "goat-owner-now-revenue-checkout-wire-20260917-01"
HOUR_URL = "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07"
HOUR_PLINK = "plink_1U8lgGATH4EDE7XDlrVYTWhu"
MUHL_URL = "https://buy.stripe.com/7sYbJ02Kpcrv9uF0Ku43S09"
SHELF = (
    {
        "sku": "sku-tip-20260826",
        "url": "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
        "plink": "plink_1U8lgOATH4EDE7XDZobVyXvE",
        "card": "land/sku-tip-20260826.md",
    },
    {
        "sku": "sku-seat-20260826",
        "url": "https://buy.stripe.com/3cIeVc5WB1MRgX7al443S03",
        "plink": "plink_1U8lgDATH4EDE7XDHtJcyv60",
        "card": "land/sku-seat-20260826.md",
    },
    {
        "sku": "sku-unlock-20260826",
        "url": "https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04",
        "plink": "plink_1U8lgEATH4EDE7XDB4w8xZu5",
        "card": "land/sku-unlock-20260826.md",
    },
    {
        "sku": "sku-monthly-tip-20260826",
        "url": "https://buy.stripe.com/bJe28qacR4Z3gX7bp843S05",
        "plink": "plink_1U8lgFATH4EDE7XDGfz9Ax3S",
        "card": "land/sku-monthly-tip-20260826.md",
    },
    {
        "sku": "sku-boost-20260826",
        "url": "https://buy.stripe.com/3cIfZgacRezDfT39h043S06",
        "plink": "plink_1U8lgFATH4EDE7XD1Ho7KkA2",
        "card": "land/sku-boost-20260826.md",
    },
)
SHELF_URLS = frozenset(row["url"] for row in SHELF)
OWNER_NOW_URLS = SHELF_URLS | {HOUR_URL}
SIBLING_RAILS = {
    "agent-rescue.html": "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
    "dealer-service-lead-rescue.html": "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "referral-intake-completeness.html": "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "repair-booking-preflight.html": "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "plant-downtime-handoff.html": "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
}
STRIPE_HREF_RE = re.compile(r'href="https://(?:buy|donate)\.stripe\.com/[^"]+"')


def _public_skus(snapshot: dict, catalog: dict) -> set[str]:
    return {row["sku"] for row in checkout_capability.project(snapshot, catalog)["public_rails"]}


class GoatOwnerNowRevenueCheckoutWire(unittest.TestCase):
    def test_exact_links_are_stored_inert_and_visible_checkout_is_renderer_owned(self) -> None:
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn('<template id="owner-now-stripe-identities">', html)
        before, tail = html.split('<template id="owner-now-stripe-identities">', 1)
        template, after = tail.split("</template>", 1)
        active_html = before + after
        noscript = html.split("<noscript>", 1)[1].split("</noscript>", 1)[0]

        self.assertGreaterEqual(html.count("js-checkout-slot"), 7)
        self.assertIn('src="./pay.js?v=20260902b"', html)
        self.assertIn('data-checkout-first="1"', html)
        self.assertIn("provider-inert", active_html)
        self.assertNotRegex(active_html, STRIPE_HREF_RE)
        self.assertNotRegex(noscript, STRIPE_HREF_RE)
        self.assertNotIn("https://buy.stripe.com/", active_html)
        self.assertNotIn("https://donate.stripe.com/", active_html)
        self.assertIn("./land/sku-whitebox-hour-20260826.md", noscript)
        self.assertIn("./land/sku-muhlnickel-titan-20260826.md", html)
        self.assertIn("Open Muhlnickel / Titan — $45,000", html)
        self.assertNotIn(MUHL_URL, html)

        self.assertEqual(
            checkout_capability.live_stripe_checkout_urls(html), OWNER_NOW_URLS
        )
        self.assertEqual(
            checkout_capability.html_stripe_url_errors("owner-now-revenue.html", html), []
        )
        self.assertEqual(
            payment_capability.html_stripe_url_errors("owner-now-revenue.html", html), []
        )

        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        listings = {row["id"]: row for row in catalog["listings"]}
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        rails = {row["sku"]: row for row in snapshot["canonical_rails"]}
        for row in SHELF:
            with self.subTest(sku=row["sku"]):
                self.assertIn(row["url"], template)
                self.assertNotIn(row["url"], active_html)
                sku_card = (ROOT / row["card"]).read_text(encoding="utf-8")
                self.assertIn(row["url"], sku_card)
                self.assertIn(row["plink"], sku_card)
                listing = listings[row["sku"]]
                self.assertEqual(listing["checkout"]["url"], row["url"])
                self.assertEqual(listing["checkout"]["status"], "ACTIVE_CHARGEABLE")
                rail = rails[row["sku"]]
                self.assertEqual(rail["url"], row["url"])
                self.assertEqual(rail["plink"], row["plink"])
                self.assertTrue(rail["livemode"])

        self.assertIn(HOUR_URL, template)
        self.assertNotIn(HOUR_URL, active_html)
        hour_card = (ROOT / "land/sku-whitebox-hour-20260826.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(HOUR_URL, hour_card)
        self.assertIn(HOUR_PLINK, hour_card)
        hour_listing = listings["sku-whitebox-hour-20260826"]
        self.assertEqual(hour_listing["checkout"]["url"], HOUR_URL)
        self.assertEqual(hour_listing["checkout"]["status"], "ACTIVE_CHARGEABLE")
        hour_rail = rails["sku-whitebox-hour-20260826"]
        self.assertEqual(hour_rail["url"], HOUR_URL)
        self.assertEqual(hour_rail["plink"], HOUR_PLINK)
        self.assertTrue(hour_rail["livemode"])
        self.assertEqual(cli.landing_surface_errors(ROOT), [])

        extra = html.replace(
            SHELF[0]["url"],
            SHELF[0]["url"] + "\nhttps://buy.stripe.com/not-a-canonical-link",
            1,
        )
        expected = [
            "owner-now-revenue.html convert shelf must reuse exactly the existing owner-now Stripe URLs"
        ]
        self.assertEqual(
            checkout_capability.html_stripe_url_errors("owner-now-revenue.html", extra),
            expected,
        )
        self.assertEqual(
            payment_capability.html_stripe_url_errors("owner-now-revenue.html", extra),
            expected,
        )

    def test_provider_and_catalog_failure_predecessors_cannot_publish_owner_now(self) -> None:
        html = PAGE.read_text(encoding="utf-8")
        before, tail = html.split('<template id="owner-now-stripe-identities">', 1)
        _template, after = tail.split("</template>", 1)
        active_html = before + after
        self.assertNotRegex(active_html, STRIPE_HREF_RE)

        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        sku = SHELF[0]["sku"]
        url = SHELF[0]["url"]
        self.assertIn(sku, _public_skus(snapshot, catalog))

        provider_not_ready = copy.deepcopy(snapshot)
        provider_not_ready["provider"]["payouts_enabled"] = False
        self.assertNotIn(sku, _public_skus(provider_not_ready, catalog))

        listing_inactive = copy.deepcopy(catalog)
        listing = next(row for row in listing_inactive["listings"] if row["id"] == sku)
        listing["checkout"]["status"] = "INERT"
        self.assertNotIn(sku, _public_skus(snapshot, listing_inactive))

        link_inactive = copy.deepcopy(snapshot)
        rail = next(row for row in link_inactive["canonical_rails"] if row["sku"] == sku)
        rail["link_active"] = False
        self.assertNotIn(sku, _public_skus(link_inactive, catalog))

        duplicate = copy.deepcopy(snapshot)
        duplicate["inert_duplicate_urls"] = list(duplicate["inert_duplicate_urls"]) + [url]
        self.assertNotIn(sku, _public_skus(duplicate, catalog))

        mismatch = copy.deepcopy(snapshot)
        rail = next(row for row in mismatch["canonical_rails"] if row["sku"] == sku)
        rail["url"] = "https://buy.stripe.com/canonical-mismatch"
        self.assertNotIn(sku, _public_skus(mismatch, catalog))

        pay_js = (ROOT / "pay.js").read_text(encoding="utf-8")
        self.assertIn("if (!railEligible(snapshot, listing))", pay_js)
        self.assertIn("Provider rail is inert. Unverified URLs stay unpublished.", pay_js)
        self.assertIn("Catalog unavailable:", pay_js)
        self.assertIn("Stripe URLs stay inert.", pay_js)

    def test_autopsy_and_199_sibling_doors_keep_their_existing_rails(self) -> None:
        page = PAGE.read_text(encoding="utf-8")
        for route, url in SIBLING_RAILS.items():
            with self.subTest(route=route):
                text = (ROOT / route).read_text(encoding="utf-8")
                self.assertIn(url, text)
                self.assertNotIn(url, page)
                for row in SHELF:
                    self.assertNotIn(row["url"], text)
                self.assertNotIn(HOUR_URL, text)
        self.assertTrue((ROOT / "p" / f"{CLAIM}.md").is_file())


if __name__ == "__main__":
    unittest.main()
