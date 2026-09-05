#!/usr/bin/env python3
"""Hermetic: four $199 diagnostic pages carry post-pay receipt→handoff copy."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGES = (
    (
        "dealer-service-lead-rescue.html",
        "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    ),
    (
        "referral-intake-completeness.html",
        "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    ),
    (
        "plant-downtime-handoff.html",
        "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
    ),
    (
        "repair-booking-preflight.html",
        "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    ),
)


class TestForgeDiagPostpayReceiptHandoff(unittest.TestCase):
    def test_four_pages_have_postpay_handoff(self) -> None:
        for path, plink in PAGES:
            with self.subTest(path=path):
                raw = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn('data-postpay-handoff="1"', raw)
                self.assertIn("After purchase", raw)
                self.assertIn("Stripe receipt", raw)
                self.assertIn("mailto:tokenjunkielabs@gmail.com", raw)
                self.assertIn(plink, raw)


if __name__ == "__main__":
    unittest.main()
