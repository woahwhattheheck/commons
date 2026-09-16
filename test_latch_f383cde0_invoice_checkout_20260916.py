#!/usr/bin/env python3
"""LATCH leftover: invoice-exception-pack catalog checkout after f383cde0 battery."""
from __future__ import annotations

import unittest
from pathlib import Path

import test_checkout_landing_integrity as cli

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "invoice-exception-pack.html"


class LatchF383InvoiceCheckout(unittest.TestCase):
    def test_catalog_slot_binds_without_static_stripe(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('class="js-checkout-slot"', text)
        self.assertEqual(text.count('data-sku="invoice-exception-pack"'), 1)
        self.assertIn("pay.js", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("diagnostic.html", text)
        self.assertIn("commercial.html", text)
        self.assertIn("</ul></article>", text)
        self.assertNotIn("</ul><  <p", text)
        self.assertEqual(cli.landing_surface_errors(ROOT), [])


if __name__ == "__main__":
    unittest.main()
