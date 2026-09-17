#!/usr/bin/env python3
"""Predecessor killers for owner-now revenue checkout publication authority.

The public owner-now page may advertise offers and local product cards, but a
Stripe checkout href is published only by pay.js after the retained provider,
catalog, and canonical-rail evidence all agree.  Static/noscript HTML must
therefore remain provider-inert.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "owner-now-revenue.html"
CATALOG = ROOT / "revenue" / "outcome_commerce" / "catalog.json"
SNAPSHOT = ROOT / "revenue" / "checkout_capability" / "snapshot.json"

EXPECTED_SKUS = (
    "sku-tip-20260826",
    "sku-seat-20260826",
    "sku-unlock-20260826",
    "sku-monthly-tip-20260826",
    "sku-boost-20260826",
    "sku-whitebox-hour-20260826",
    "sku-muhlnickel-titan-20260826",
)
GATED_STRIPE_SKUS = EXPECTED_SKUS[:-1]
EXPECTED_RECORDED_URLS = {
    "sku-tip-20260826": "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
    "sku-seat-20260826": "https://buy.stripe.com/3cIeVc5WB1MRgX7al443S03",
    "sku-unlock-20260826": "https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04",
    "sku-monthly-tip-20260826": "https://buy.stripe.com/bJe28qacR4Z3gX7bp843S05",
    "sku-boost-20260826": "https://buy.stripe.com/3cIfZgacRezDfT39h043S06",
    "sku-whitebox-hour-20260826": "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
}
STRIPE_HREF = re.compile(r'href\s*=\s*["\']https://(?:buy|donate)\.stripe\.com/', re.I)
STRIPE_TEXT = re.compile(r'https://(?:buy|donate)\.stripe\.com/', re.I)


def _load_checkout_capability():
    path = ROOT / "host" / "checkout_capability.py"
    spec = importlib.util.spec_from_file_location("zeta_owner_now_checkout_capability", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("checkout capability module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


capability = _load_checkout_capability()


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.slots: list[str] = []
        self.hrefs: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"])
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if "js-checkout-slot" in set(values.get("class", "").split()):
            self.slots.append(values.get("data-sku", ""))


class OwnerNowRevenueGatedCheckout(unittest.TestCase):
    def setUp(self) -> None:
        self.html = PAGE.read_text(encoding="utf-8")
        self.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        self.parser = _PageParser()
        self.parser.feed(self.html)
        self.parser.close()

    def _public(self, snapshot=None, catalog=None):
        projected = capability.project(snapshot or self.snapshot, catalog or self.catalog)
        return {row["sku"]: row for row in projected["public_rails"]}

    def _listing(self, catalog: dict, sku: str) -> dict:
        return next(row for row in catalog["listings"] if row.get("id") == sku)

    def _rail(self, snapshot: dict, sku: str) -> dict:
        return next(row for row in snapshot["canonical_rails"] if row.get("sku") == sku)

    def test_static_and_noscript_surface_cannot_publish_stripe(self) -> None:
        self.assertIsNone(STRIPE_HREF.search(self.html))
        self.assertIsNone(STRIPE_TEXT.search(self.html))
        self.assertIn("<noscript>", self.html)
        noscript = self.html.split("<noscript>", 1)[1].split("</noscript>", 1)[0]
        self.assertIsNone(STRIPE_TEXT.search(noscript))
        self.assertIn("mailto:tokenjunkielabs@gmail.com", noscript)
        self.assertIn("capability gate cannot run", noscript)

    def test_slots_bind_exactly_once_and_local_product_routes_survive(self) -> None:
        self.assertEqual(Counter(self.parser.slots), Counter(EXPECTED_SKUS))
        self.assertTrue(any(src.split("?", 1)[0].endswith("pay.js") for src in self.parser.scripts))
        for sku in EXPECTED_SKUS:
            self.assertIn(f"./land/{sku}.md", self.parser.hrefs)
        self.assertIn("./land/sku-muhlnickel-titan-20260826.md", self.parser.hrefs)
        self.assertIn("mailto:tokenjunkielabs@gmail.com", self.parser.hrefs)

    def test_recorded_six_link_identities_still_match_catalog_and_snapshot(self) -> None:
        rails = {row["sku"]: row for row in self.snapshot["canonical_rails"]}
        listings = {row["id"]: row for row in self.catalog["listings"]}
        for sku, expected in EXPECTED_RECORDED_URLS.items():
            with self.subTest(sku=sku):
                checkout = listings[sku]["checkout"]
                rail = rails[sku]
                self.assertEqual(checkout["url"], expected)
                self.assertEqual(checkout["status"], "ACTIVE_CHARGEABLE")
                self.assertIs(checkout["link_active"], True)
                self.assertIs(checkout["account_charges_enabled"], True)
                self.assertIs(checkout["account_payouts_enabled"], True)
                self.assertEqual(rail["url"], expected)
                self.assertIs(rail["link_active"], True)
                self.assertIs(rail["livemode"], True)

    def test_provider_not_ready_drops_every_owner_now_public_rail(self) -> None:
        dead = copy.deepcopy(self.snapshot)
        dead["provider"]["payouts_enabled"] = False
        public = self._public(snapshot=dead)
        for sku in GATED_STRIPE_SKUS:
            self.assertNotIn(sku, public)

    def test_listing_inactive_or_link_inactive_drops_that_rail(self) -> None:
        for field, value in (("status", "INERT"), ("link_active", False)):
            with self.subTest(field=field):
                catalog = copy.deepcopy(self.catalog)
                checkout = self._listing(catalog, "sku-tip-20260826")["checkout"]
                checkout[field] = value
                self.assertNotIn("sku-tip-20260826", self._public(catalog=catalog))

    def test_canonical_rail_mismatch_or_inert_duplicate_drops_that_rail(self) -> None:
        mismatch = copy.deepcopy(self.snapshot)
        self._rail(mismatch, "sku-tip-20260826")["url"] = (
            "https://donate.stripe.com/not_the_catalog_rail"
        )
        self.assertNotIn("sku-tip-20260826", self._public(snapshot=mismatch))

        duplicate = copy.deepcopy(self.snapshot)
        duplicate["inert_duplicate_urls"] = list(duplicate.get("inert_duplicate_urls") or []) + [
            EXPECTED_RECORDED_URLS["sku-tip-20260826"]
        ]
        self.assertNotIn("sku-tip-20260826", self._public(snapshot=duplicate))

    def test_renderer_fail_closed_paths_remain_explicit(self) -> None:
        pay_js = (ROOT / "pay.js").read_text(encoding="utf-8")
        required = (
            'checkout.status !== "ACTIVE_CHARGEABLE"',
            "checkout.link_active !== true",
            "checkout.account_charges_enabled !== true",
            "checkout.account_payouts_enabled !== true",
            "canonicalRailMatches(snapshot, listing)",
            "inert_duplicate_urls",
            "Catalog unavailable:",
            "Stripe URLs stay inert.",
        )
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, pay_js)


if __name__ == "__main__":
    unittest.main()
