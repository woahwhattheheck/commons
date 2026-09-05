#!/usr/bin/env python3
"""Hermetic pin: four live $199 diagnostics on commerce tip shelf."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMERCE = ROOT / "commerce.html"

DIAGNOSTICS = (
    (
        "sku-dealer-service-lead-rescue",
        "Dealer Service Lead Rescue",
        "./dealer-service-lead-rescue.html",
        "Open $199 dealer diagnostic",
    ),
    (
        "sku-referral-intake-completeness",
        "Referral Intake Completeness",
        "./referral-intake-completeness.html",
        "Open $199 referral diagnostic",
    ),
    (
        "sku-repair-booking-preflight",
        "Repair Booking Preflight",
        "./repair-booking-preflight.html",
        "Open $199 repair diagnostic",
    ),
    (
        "sku-plant-downtime-handoff",
        "Plant Downtime Handoff",
        "./plant-downtime-handoff.html",
        "Open $199 plant diagnostic",
    ),
)

# Live checkouts stay on product pages — never invent plinks on commerce.
FORBIDDEN_PLINKS = (
    "buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
)


class TestForgeCommerceDiagnosticTipShelf(unittest.TestCase):
    def test_tip_shelf_surfaces_four_199_diagnostics(self) -> None:
        raw = COMMERCE.read_text(encoding="utf-8")
        self.assertIn("$199 once", raw)
        for sku_id, title, href, cta in DIAGNOSTICS:
            with self.subTest(sku=sku_id):
                self.assertIn(f'id="{sku_id}"', raw)
                self.assertIn(title, raw)
                self.assertIn(f'href="{href}"', raw)
                self.assertIn(cta, raw)
        for plink in FORBIDDEN_PLINKS:
            self.assertNotIn(plink, raw)


if __name__ == "__main__":
    unittest.main()
