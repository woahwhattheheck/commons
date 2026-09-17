#!/usr/bin/env python3
"""Regression contract for deriving fixed checkout CTAs from canonical product pages."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PAY = (ROOT / "pay.js").read_text(encoding="utf-8")
SURFACES = {
    "tips.html": "live-cash-doors",
    "commerce.html": "tip-shelf",
    "bazaar.html": "live-cash",
    "tools-cash.html": "cash-doors",
}
CONVERT_SURFACES = ("bazaar.html", "tools-cash.html")
INERT_SURFACES = ("tips.html", "commerce.html")
PRODUCTS = {
    "hotel-room-turn-evidence.html": "https://buy.stripe.com/7sYdR8ckZgHLbCN50K43S0y",
    "late-cancel-noshow-fee-leakage.html": "https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x",
    "chargeback-evidence-readiness.html": "https://buy.stripe.com/28E9AS70F6378qB2SC43S0w",
}


class FixedBuyShelfConvertTests(unittest.TestCase):
    def test_four_surfaces_load_one_payment_hydrator_and_publish_product_scope_links(self):
        for page_name, container_id in SURFACES.items():
            with self.subTest(page=page_name):
                page = (ROOT / page_name).read_text(encoding="utf-8")
                self.assertIn(f'id="{container_id}"', page)
                self.assertRegex(page, r'<script src="\./pay\.js\?v=[^"]+"></script>')
                for product in PRODUCTS:
                    self.assertIn(f'href="./{product}"', page)

    def test_hydrator_names_all_four_surfaces_and_only_the_three_fixed_product_pages(self):
        self.assertIn("(?:tips|commerce|bazaar|tools-cash)\\.html", PAY)
        for container_id in SURFACES.values():
            self.assertIn(f"#{container_id}", PAY)
        for product in PRODUCTS:
            self.assertIn(f'path: "./{product}"', PAY)

    def test_direct_fixed_urls_are_owned_by_product_pages_not_reminted_into_shelves_or_js(self):
        for product, expected_url in PRODUCTS.items():
            product_page = (ROOT / product).read_text(encoding="utf-8")
            self.assertGreaterEqual(product_page.count(expected_url), 2)
            self.assertNotIn(expected_url, PAY)
            for surface in INERT_SURFACES:
                self.assertNotIn(
                    expected_url,
                    (ROOT / surface).read_text(encoding="utf-8"),
                    surface,
                )
            for surface in CONVERT_SURFACES:
                self.assertIn(
                    expected_url,
                    (ROOT / surface).read_text(encoding="utf-8"),
                    surface,
                )

    def test_checkout_derivation_fails_closed(self):
        self.assertIn('if (!container || !accountReady(snapshot) || typeof fetch !== "function") return;', PAY)
        self.assertIn('fetch(product.path, { cache: "no-store" })', PAY)
        self.assertIn('parsed.querySelectorAll("a[href]")', PAY)
        self.assertIn("if (isStripeCheckoutUrl(href)) seen[href] = true;", PAY)
        self.assertIn('return urls.length === 1 ? urls[0] : "";', PAY)
        self.assertIn('if (!parent || !isStripeCheckoutUrl(url)) return;', PAY)
        self.assertIn('data-fixed-buy-road', PAY)
        self.assertIn('rel", "noopener noreferrer', PAY)
        self.assertIn('target", "_blank', PAY)
        self.assertRegex(PAY, r'\.catch\(function \(\) \{\s*// Canonical product page or rail proof unavailable')

    def test_product_pages_keep_truth_boundary_next_to_live_checkout(self):
        markers = (
            "Economic truth:",
            "intent",
            "provider",
        )
        for product in PRODUCTS:
            with self.subTest(product=product):
                page = (ROOT / product).read_text(encoding="utf-8")
                for marker in markers:
                    self.assertIn(marker.lower(), page.lower())
                self.assertIsNone(re.search(r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{12,}", page))


if __name__ == "__main__":
    unittest.main()
