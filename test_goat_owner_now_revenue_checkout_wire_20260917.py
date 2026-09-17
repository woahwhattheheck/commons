#!/usr/bin/env python3
"""GOAT owner-now source carrier retained; post-merge checkout authority is gated.

GOAT keeps source/product/link-discovery credit from PR #15364.  The static and
noscript Stripe publication it introduced was stopped after merge.  This module
reuses the post-merge predecessor suite so the original carrier filename stays a
retained proof surface without re-authorizing the stopped behavior.
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
