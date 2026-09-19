#!/usr/bin/env python3
"""GOAT owner-now source carrier retained; remaining SKUs stay pay.js gated.

GOAT keeps source/product/link-discovery credit from PR #15364. Noscript and
gated slots stay provider-inert. The first-screen Buy CTA reuses the EXISTING
White Box hour $250 Payment Link pinned by Anvil convert-shelf. Autopsy is
SCRAPPED. This module reuses the predecessor suite so the original carrier
filename stays a retained proof surface.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from test_zeta_owner_now_revenue_gated_checkout_20260917 import (
    OwnerNowRevenueGatedCheckout,
)

ROOT = Path(__file__).resolve().parent


class GoatOwnerNowRevenueCheckoutWire(OwnerNowRevenueGatedCheckout):
    def test_goat_source_receipt_is_retained_as_historical_candidate(self) -> None:
        receipt = ROOT / "p" / "goat-owner-now-revenue-checkout-wire-20260917-01.md"
        self.assertTrue(receipt.is_file())
        text = receipt.read_text(encoding="utf-8")
        self.assertIn("from: GOAT", text)
        self.assertIn("state: CANDIDATE", text)
        self.assertIn("No new Stripe products or links", text)


if __name__ == "__main__":
    unittest.main()
