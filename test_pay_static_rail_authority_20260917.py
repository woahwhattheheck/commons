#!/usr/bin/env python3
"""Post-merge authority closure for Commons #15406 static pay rails.

The LOW+WIDE tip shelf and White Box hour remain real catalog/SKU evidence,
but pay.html may publish their Stripe anchors only through pay.js::railEligible.
Static HTML and no-JS fallback are not provider-authenticated capability proof.
"""
from __future__ import annotations

import importlib.util
import re
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
RUNTIME_ONLY_RAILS = (
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
STRIPE_RE = re.compile(r"https://(?:buy|donate)\.stripe\.com/[A-Za-z0-9_-]+")


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


class TestPay15406StaticRailAuthorityClosure(unittest.TestCase):
    def test_runtime_only_rails_are_not_static_or_noscript(self) -> None:
        html = PAY.read_text(encoding="utf-8")
        self.assertEqual(
            checkout_capability.live_stripe_checkout_urls(html), TYPE_PRODUCT_BUYS
        )
        self.assertEqual(
            payment_capability.live_stripe_checkout_urls(html), TYPE_PRODUCT_BUYS
        )
        tail = html.split("<h2>LOW + WIDE</h2>", 1)[1]
        for url in RUNTIME_ONLY_RAILS:
            with self.subTest(url=url):
                self.assertNotIn(url, tail)
        if "<noscript>" in html:
            noscript = html.split("<noscript>", 1)[1].split("</noscript>", 1)[0]
            self.assertIsNone(STRIPE_RE.search(noscript))
        for sku in RUNTIME_SKUS:
            with self.subTest(sku=sku):
                self.assertIn(f'data-sku="{sku}"', html)
        self.assertIn('src="./pay.js?v=20260902a"', html)

    def test_both_static_validators_reject_each_runtime_only_rail(self) -> None:
        html = PAY.read_text(encoding="utf-8")
        marker = "<h2>LOW + WIDE</h2>"
        self.assertIn(marker, html)
        for url in RUNTIME_ONLY_RAILS:
            with self.subTest(url=url):
                forged = html.replace(
                    marker,
                    marker + f'\n<a class="checkout-active" href="{url}">forged</a>',
                    1,
                )
                self.assertTrue(
                    checkout_capability.html_stripe_url_errors("pay.html", forged)
                )
                self.assertTrue(
                    payment_capability.html_stripe_url_errors("pay.html", forged)
                )

    def test_pay_specific_static_runtime_allowlist_is_absent(self) -> None:
        self.assertFalse(
            hasattr(checkout_capability, "PAY_CONVERT_SHELF_LIVE_CHECKOUTS")
        )
        self.assertFalse(
            hasattr(payment_capability, "PAY_CONVERT_SHELF_LIVE_CHECKOUTS")
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

    def test_positive_static_regression_suite_is_retired(self) -> None:
        self.assertFalse(
            (ROOT / "test_goat_pay_tipshelf_checkout_wire_20260917.py").exists()
        )


if __name__ == "__main__":
    unittest.main()
