#!/usr/bin/env python3
"""LATCH leftover: invoice-exception-pack catalog checkout after f383cde0 battery.

GOAT convert leftover `goat-invoice-exception-pack-checkout-wire-20260916-01`
wires the existing verified Payment Link as a static CTA so checkout does not
wait on catalog hydration. Larger-fixed KEEP and well-formed article stay.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import test_checkout_landing_integrity as cli

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "invoice-exception-pack.html"
CHECKOUT_URL = "https://buy.stripe.com/14A00i84Jdvz36hdxg43S0l"


class LatchF383InvoiceCheckout(unittest.TestCase):
    def test_verified_checkout_url_and_larger_fixed_keep(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn(CHECKOUT_URL, text)
        self.assertNotIn('class="js-checkout-slot"', text)
        self.assertNotIn("pay.js", text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn("diagnostic.html", text)
        self.assertIn("commercial.html", text)
        self.assertIn("</ul></article>", text)
        self.assertNotIn("</ul><  <p", text)
        self.assertEqual(cli.landing_surface_errors(ROOT), [])


if __name__ == "__main__":
    unittest.main()
