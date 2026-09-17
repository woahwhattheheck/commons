#!/usr/bin/env python3
"""Post-merge predecessor killers for pay.html checkout publication authority.

#15406 landed LOW+WIDE and White Box Payment Links directly in static and
noscript HTML.  Those six rails are retained evidence, but they are public
checkout authority only after the existing provider/catalog/canonical-rail
gate succeeds.  This suite keeps the static pay surface inert for those rails
while preserving the already-authorized fixed product-door buy links.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "pay.html"
CATALOG = ROOT / "revenue" / "outcome_commerce" / "catalog.json"
SNAPSHOT = ROOT / "revenue" / "checkout_capability" / "snapshot.json"
PAY_JS = ROOT / "pay.js"

GATED_SKUS = (
    "sku-tip-20260826",
    "sku-seat-20260826",
    "sku-unlock-20260826",
    "sku-monthly-tip-20260826",
    "sku-boost-20260826",
    "sku-whitebox-hour-20260826",
)
ALL_DYNAMIC_SKUS = GATED_SKUS + ("sku-muhlnickel-titan-20260826",)
GATED_URLS = {
    "sku-tip-20260826": "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
    "sku-seat-20260826": "https://buy.stripe.com/3cIeVc5WB1MRgX7al443S03",
    "sku-unlock-20260826": "https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04",
    "sku-monthly-tip-20260826": "https://buy.stripe.com/bJe28qacR4Z3gX7bp843S05",
    "sku-boost-20260826": "https://buy.stripe.com/3cIfZgacRezDfT39h043S06",
    "sku-whitebox-hour-20260826": "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
}


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


capability = _load_module(ROOT / "host" / "checkout_capability.py", "zsol_pay_checkout_capability")


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.slots: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if "js-checkout-slot" in set(values.get("class", "").split()):
            self.slots.append(values.get("data-sku", ""))


class PayPostmergeRailAuthorityClosure(unittest.TestCase):
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

    @staticmethod
    def _listing(catalog: dict, sku: str) -> dict:
        return next(row for row in catalog["listings"] if row.get("id") == sku)

    @staticmethod
    def _rail(snapshot: dict, sku: str) -> dict:
        return next(row for row in snapshot["canonical_rails"] if row.get("sku") == sku)

    def test_lowwide_and_whitebox_urls_are_not_static_or_noscript_authority(self) -> None:
        for sku, url in GATED_URLS.items():
            with self.subTest(sku=sku):
                self.assertNotIn(url, self.html)
        if "<noscript>" in self.html:
            noscript = self.html.split("<noscript>", 1)[1].split("</noscript>", 1)[0]
            for sku, url in GATED_URLS.items():
                with self.subTest(noscript_sku=sku):
                    self.assertNotIn(url, noscript)

    def test_each_dynamic_pay_sku_keeps_exactly_one_runtime_slot(self) -> None:
        counts = Counter(self.parser.slots)
        for sku in ALL_DYNAMIC_SKUS:
            with self.subTest(sku=sku):
                self.assertEqual(counts[sku], 1)
        self.assertTrue(any(src.split("?", 1)[0].endswith("pay.js") for src in self.parser.scripts))

    def test_six_recorded_link_identities_remain_in_catalog_and_snapshot(self) -> None:
        listings = {row["id"]: row for row in self.catalog["listings"]}
        rails = {row["sku"]: row for row in self.snapshot["canonical_rails"]}
        for sku, expected in GATED_URLS.items():
            with self.subTest(sku=sku):
                checkout = listings[sku]["checkout"]
                rail = rails[sku]
                self.assertEqual(checkout["url"], expected)
                self.assertEqual(rail["url"], expected)
                self.assertEqual(checkout["status"], "ACTIVE_CHARGEABLE")
                self.assertIs(checkout["link_active"], True)
                self.assertIs(rail["link_active"], True)
                self.assertIs(rail["livemode"], True)

    def test_provider_not_ready_drops_all_six_gated_rails(self) -> None:
        dead = copy.deepcopy(self.snapshot)
        dead["provider"]["payouts_enabled"] = False
        public = self._public(snapshot=dead)
        for sku in GATED_SKUS:
            with self.subTest(sku=sku):
                self.assertNotIn(sku, public)

    def test_listing_or_link_inactive_drops_affected_rail(self) -> None:
        for field, value in (("status", "INERT"), ("link_active", False)):
            with self.subTest(field=field):
                catalog = copy.deepcopy(self.catalog)
                self._listing(catalog, "sku-tip-20260826")["checkout"][field] = value
                self.assertNotIn("sku-tip-20260826", self._public(catalog=catalog))

    def test_canonical_mismatch_or_inert_duplicate_drops_affected_rail(self) -> None:
        mismatch = copy.deepcopy(self.snapshot)
        self._rail(mismatch, "sku-tip-20260826")["url"] = "https://donate.stripe.com/not_the_catalog_rail"
        self.assertNotIn("sku-tip-20260826", self._public(snapshot=mismatch))

        duplicate = copy.deepcopy(self.snapshot)
        duplicate["inert_duplicate_urls"] = list(duplicate.get("inert_duplicate_urls") or []) + [
            GATED_URLS["sku-tip-20260826"]
        ]
        self.assertNotIn("sku-tip-20260826", self._public(snapshot=duplicate))

    def test_renderer_retains_every_fail_closed_gate_and_fetch_failure_path(self) -> None:
        pay_js = PAY_JS.read_text(encoding="utf-8")
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

    def test_host_validators_do_not_reintroduce_pay_static_allowlist_exception(self) -> None:
        for rel in ("host/checkout_capability.py", "host/payment_capability.py"):
            source = (ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(path=rel):
                self.assertNotIn("PAY_CONVERT_SHELF_LIVE_CHECKOUTS", source)
                self.assertNotIn('if name == "pay.html":\n        found = live_stripe_checkout_urls', source)


if __name__ == "__main__":
    unittest.main()
