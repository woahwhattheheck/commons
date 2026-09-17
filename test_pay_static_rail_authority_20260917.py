#!/usr/bin/env python3
"""Compose leftover with #15413: static tip-shelf CTAs + pay.js hydrate stay.

LOW+WIDE tip-shelf and White Box hour reuse existing livemode Payment Links as
static/noscript primary CTAs (same class as tips.html). Catalog slots and
pay.js::railEligible remain. Type product buys stay in #buy-now-live-checkout.
No invented Stripe URLs. Extra URLs still fail both capability validators.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PAY = ROOT / "pay.html"
PAY_JS = ROOT / "pay.js"

TYPE_PRODUCT_BUYS = frozenset(
    {
        "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
        "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
        "https://buy.stripe.com/28E9AS70F6378qB2SC43S0w",
        "https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x",
        "https://buy.stripe.com/7sYdR8ckZgHLbCN50K43S0y",
    }
)
TIP_SHELF_RAILS = (
    "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
    "https://buy.stripe.com/3cIeVc5WB1MRgX7al443S03",
    "https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04",
    "https://buy.stripe.com/bJe28qacR4Z3gX7bp843S05",
    "https://buy.stripe.com/3cIfZgacRezDfT39h043S06",
    "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
)
RUNTIME_SKUS = (
    "sku-tip-20260826",
    "sku-seat-20260826",
    "sku-unlock-20260826",
    "sku-monthly-tip-20260826",
    "sku-boost-20260826",
    "sku-whitebox-hour-20260826",
)
MUHL_URL = "https://buy.stripe.com/7sYbJ02Kpcrv9uF0Ku43S09"


def _load_host(name: str):
    path = ROOT / "host" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"pay15406_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checkout_capability = _load_host("checkout_capability")
payment_capability = _load_host("payment_capability")
PAY_URLS = TYPE_PRODUCT_BUYS | set(TIP_SHELF_RAILS)


class TestPay15406StaticRailAuthorityClosure(unittest.TestCase):
    def test_tip_shelf_static_ctas_reuse_existing_links_and_keep_slots(self) -> None:
        html = PAY.read_text(encoding="utf-8")
        self.assertEqual(
            checkout_capability.live_stripe_checkout_urls(html), PAY_URLS
        )
        self.assertEqual(
            payment_capability.live_stripe_checkout_urls(html), PAY_URLS
        )
        tail = html.split("<h2>LOW + WIDE</h2>", 1)[1]
        noscript = html.split("<noscript>", 1)[1].split("</noscript>", 1)[0]
        for url in TIP_SHELF_RAILS:
            with self.subTest(url=url):
                self.assertIn(url, tail)
                self.assertIn(url, noscript)
        for sku in RUNTIME_SKUS:
            with self.subTest(sku=sku):
                self.assertIn(f'data-sku="{sku}"', html)
        self.assertIn('src="./pay.js?v=20260902a"', html)
        self.assertIn("./land/sku-muhlnickel-titan-20260826.md", html)
        self.assertNotIn(MUHL_URL, html)
        buy_now = html.split('id="buy-now-live-checkout"', 1)[1].split(
            'id="owner-action"', 1
        )[0]
        self.assertEqual(checkout_capability.live_buy_urls(buy_now), TYPE_PRODUCT_BUYS)

    def test_both_static_validators_reject_an_invented_stripe_url(self) -> None:
        html = PAY.read_text(encoding="utf-8")
        forged = html.replace(
            TIP_SHELF_RAILS[0],
            TIP_SHELF_RAILS[0] + "\nhttps://buy.stripe.com/not-a-canonical-link",
            1,
        )
        self.assertEqual(
            checkout_capability.html_stripe_url_errors("pay.html", forged),
            ["pay.html convert shelf must reuse exactly the existing pay Stripe URLs"],
        )
        self.assertEqual(
            payment_capability.html_stripe_url_errors("pay.html", forged),
            ["pay.html convert shelf must reuse exactly the existing pay Stripe URLs"],
        )

    def test_pay_convert_shelf_allowlist_is_type_buys_plus_existing_tip_and_hour(self) -> None:
        self.assertEqual(
            checkout_capability.PAY_CONVERT_SHELF_LIVE_CHECKOUTS, PAY_URLS
        )
        self.assertEqual(
            payment_capability.PAY_CONVERT_SHELF_LIVE_CHECKOUTS, PAY_URLS
        )
        self.assertEqual(
            checkout_capability.CONVERT_SHELF_LIVE_BUYS["pay.html"],
            TYPE_PRODUCT_BUYS,
        )
        self.assertEqual(
            payment_capability.CONVERT_SHELF_LIVE_BUYS["pay.html"],
            TYPE_PRODUCT_BUYS,
        )

    def test_runtime_gate_keeps_every_current_authority_predicate(self) -> None:
        js = PAY_JS.read_text(encoding="utf-8")
        required = (
            "function railEligible(snapshot, listing)",
            "if (!accountReady(snapshot)) return false;",
            'if (checkout.status !== "ACTIVE_CHARGEABLE") return false;',
            "if (checkout.link_active !== true) return false;",
            "if (!hasDurableCapabilityEvidence(checkout)) return false;",
            "if (!canonicalRailMatches(snapshot, listing)) return false;",
            "snapshot.inert_duplicate_urls || []",
            "if (!railEligible(snapshot, listing))",
            "Stripe URLs stay inert.",
        )
        for fragment in required:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, js)

    def test_positive_static_leftover_suite_is_present(self) -> None:
        self.assertTrue(
            (ROOT / "test_goat_pay_tipshelf_checkout_wire_20260917.py").is_file()
        )
        self.assertTrue(
            (ROOT / "p" / "goat-pay-tipshelf-checkout-wire-20260917-01.md").is_file()
        )


if __name__ == "__main__":
    unittest.main()
