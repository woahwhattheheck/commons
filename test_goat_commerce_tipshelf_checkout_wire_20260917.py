#!/usr/bin/env python3
"""Hermetic: commerce.html tip-shelf buy-path uses existing Payment Links."""
from __future__ import annotations

import importlib.util
import json
import re
import unittest
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

import test_checkout_landing_integrity as cli
import test_type_commerce_convert_shelf_20260917_01 as type_shelf

ROOT = Path(__file__).resolve().parent


def _load_host(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "host" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checkout_capability = _load_host("checkout_capability")
payment_capability = _load_host("payment_capability")
PAGE = ROOT / "commerce.html"
CATALOG = ROOT / "revenue/outcome_commerce/catalog.json"
SNAPSHOT = ROOT / "revenue/checkout_capability/snapshot.json"
CLAIM = "goat-commerce-tipshelf-checkout-wire-20260917-01"
HOUR_URL = "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07"
HOUR_PLINK = "plink_1U8lgGATH4EDE7XDlrVYTWhu"
MUHL_URL = "https://buy.stripe.com/7sYbJ02Kpcrv9uF0Ku43S09"
TYPE_PRODUCT_BUYS = type_shelf.ALLOWED_LIVE_BUY_URLS
SHELF = (
    {
        "sku": "sku-tip-20260826",
        "url": "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
        "plink": "plink_1U8lgOATH4EDE7XDZobVyXvE",
        "cta": "Buy tip — $5",
        "card": "land/sku-tip-20260826.md",
    },
    {
        "sku": "sku-seat-20260826",
        "url": "https://buy.stripe.com/3cIeVc5WB1MRgX7al443S03",
        "plink": "plink_1U8lgDATH4EDE7XDHtJcyv60",
        "cta": "Buy seat — $5 / month",
        "card": "land/sku-seat-20260826.md",
    },
    {
        "sku": "sku-unlock-20260826",
        "url": "https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04",
        "plink": "plink_1U8lgEATH4EDE7XDB4w8xZu5",
        "cta": "Buy unlock — $5",
        "card": "land/sku-unlock-20260826.md",
    },
    {
        "sku": "sku-monthly-tip-20260826",
        "url": "https://buy.stripe.com/bJe28qacR4Z3gX7bp843S05",
        "plink": "plink_1U8lgFATH4EDE7XDGfz9Ax3S",
        "cta": "Buy monthly tip — $3 / month",
        "card": "land/sku-monthly-tip-20260826.md",
    },
    {
        "sku": "sku-boost-20260826",
        "url": "https://buy.stripe.com/3cIfZgacRezDfT39h043S06",
        "plink": "plink_1U8lgFATH4EDE7XD1Ho7KkA2",
        "cta": "Buy boost — $4.99 / month",
        "card": "land/sku-boost-20260826.md",
    },
    {
        "sku": "sku-whitebox-hour-20260826",
        "url": HOUR_URL,
        "plink": HOUR_PLINK,
        "cta": "Buy White Box hour — $250",
        "card": "land/sku-whitebox-hour-20260826.md",
    },
)
SHELF_URLS = frozenset(row["url"] for row in SHELF)
COMMERCE_URLS = TYPE_PRODUCT_BUYS | SHELF_URLS
SIBLING_RAILS = {
    "dealer-service-lead-rescue.html": "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "referral-intake-completeness.html": "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "repair-booking-preflight.html": "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "plant-downtime-handoff.html": "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
}
TYPE_CTAS = (
    "Buy dealer diagnostic — $199",
    "Buy referral diagnostic — $199",
    "Buy repair diagnostic — $199",
    "Buy plant diagnostic — $199",
    "Buy hotel room-turn — $2,500",
    "Buy late-cancel diagnostic — $3,500",
    "Buy chargeback desk — $4,000",
    "Buy one White Box hour — $250",
)
STRIPE_HREF_RE = re.compile(r'href="(https://(?:buy|donate)\.stripe\.com/[^"]+)"')


class GoatCommerceTipshelfCheckoutWire(unittest.TestCase):
    def test_door_and_catalog_carry_the_verified_payment_links(self) -> None:
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn("<noscript>", html)
        noscript = html.split("<noscript>", 1)[1].split("</noscript>", 1)[0]
        self.assertNotIn("Static copy keeps Stripe URLs inert until catalog evidence is read.", html)
        self.assertIn("Catalog hydrate stays available; the Payment Link does not wait on it.", html)
        self.assertGreaterEqual(html.count("js-checkout-slot"), 7)
        self.assertIn('src="./pay.js?v=20260828b"', html)
        self.assertIn("./land/sku-muhlnickel-titan-20260826.md", html)
        self.assertIn("Open Muhlnickel / Titan — $45,000", html)
        self.assertNotIn(MUHL_URL, html)
        self.assertIn('id="buy-now-live-checkout"', html)
        self.assertEqual(
            checkout_capability.html_stripe_url_errors("commerce.html", html),
            [],
        )
        self.assertEqual(
            payment_capability.html_stripe_url_errors("commerce.html", html),
            [],
        )
        self.assertEqual(
            checkout_capability.live_stripe_checkout_urls(html),
            COMMERCE_URLS,
        )
        self.assertEqual(
            checkout_capability.COMMERCE_CONVERT_SHELF_LIVE_CHECKOUTS,
            COMMERCE_URLS,
        )
        self.assertEqual(SHELF_URLS, frozenset(row["url"] for row in SHELF))
        self.assertEqual(len(SHELF_URLS), 6)

        hrefs = [unescape(value) for value in STRIPE_HREF_RE.findall(html)]
        self.assertGreaterEqual(len(hrefs), 21)
        seen = set()
        for href in hrefs:
            parsed = urlsplit(href)
            canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            self.assertIn(canonical, COMMERCE_URLS)
            self.assertEqual(parsed.query, "")
            seen.add(canonical)
        self.assertEqual(seen, COMMERCE_URLS)

        buy_now = type_shelf.convert_shelf(html)
        self.assertEqual(type_shelf.live_buy_urls(buy_now), TYPE_PRODUCT_BUYS)
        self.assertNotIn("donate.stripe.com", buy_now)
        for cta in TYPE_CTAS:
            self.assertIn(cta, buy_now)

        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        listings = {row["id"]: row for row in catalog["listings"]}
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        rails = {row["sku"]: row for row in snapshot["canonical_rails"]}
        for row in SHELF:
            with self.subTest(sku=row["sku"]):
                self.assertIn(row["url"], html)
                self.assertGreaterEqual(html.count(row["url"]), 2)
                self.assertIn(row["cta"], html)
                self.assertGreaterEqual(html.count(row["cta"]), 2)
                self.assertIn(row["url"], noscript)
                self.assertIn(row["cta"], noscript)
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
        self.assertEqual(cli.landing_surface_errors(ROOT), [])

        extra = html.replace(
            SHELF[0]["url"],
            SHELF[0]["url"] + "\nhttps://buy.stripe.com/not-a-canonical-link",
            1,
        )
        self.assertEqual(
            checkout_capability.html_stripe_url_errors("commerce.html", extra),
            ["commerce.html convert shelf must reuse exactly the existing commerce Stripe URLs"],
        )

    def test_autopsy_and_199_sibling_doors_keep_their_existing_rails(self) -> None:
        page = PAGE.read_text(encoding="utf-8")
        for route, url in SIBLING_RAILS.items():
            with self.subTest(route=route):
                text = (ROOT / route).read_text(encoding="utf-8")
                self.assertIn(url, text)
                for row in SHELF:
                    if row["url"] == HOUR_URL:
                        continue
                    self.assertNotIn(row["url"], text)
                if url in TYPE_PRODUCT_BUYS:
                    self.assertIn(url, page)
        self.assertTrue((ROOT / "p" / f"{CLAIM}.md").is_file())


if __name__ == "__main__":
    unittest.main()
