#!/usr/bin/env python3
"""LATCH leftover: fleet-work-order commercial-pack catalog checkout."""
from __future__ import annotations

import unittest
from pathlib import Path

import test_checkout_landing_integrity as cli

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "fleet-work-order.html"
SKU = "fleet-work-order-exactly-once"


class LatchCommercialPackCheckout(unittest.TestCase):
    def test_catalog_slot_binds_without_static_stripe(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        parser = cli.SurfaceParser()
        parser.feed(text)
        parser.close()
        self.assertIn('class="js-checkout-slot"', text)
        self.assertEqual(text.count(f'data-sku="{SKU}"'), 1)
        self.assertEqual(parser.checkout_slots, [SKU])
        self.assertTrue(any(cli.canonical_local_pay_js(src) for src in parser.script_srcs), parser.script_srcs)
        self.assertIn("pay.js", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertTrue(any(cli.canonical_handoff_mailto(href) for href in parser.hrefs))
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("diagnostic.html", text)
        self.assertIn("commercial.html", text)
        surfaces, errors = cli.dedicated_checkout_surfaces(ROOT)
        self.assertEqual(errors, [])
        self.assertIn(SKU, surfaces.get("fleet-work-order.html", {}))
        self.assertEqual(cli.landing_surface_errors(ROOT), [])


if __name__ == "__main__":
    unittest.main()
