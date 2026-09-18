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

# Live checkouts stay on product pages as relative doors. Convert shelf
# may reuse existing live buys; exact allowlist is
# test_type_commerce_convert_shelf_20260917_01.py.


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
        self.assertIn('id="buy-now-live-checkout"', raw)


if __name__ == "__main__":
    unittest.main()
