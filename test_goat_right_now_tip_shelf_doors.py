#!/usr/bin/env python3
"""Hermetic: right-now surfaces four live $199 tip-shelf diagnostic doors."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "right-now.html"

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

FORBIDDEN_PLINKS = (
    "buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
)


class TestGoatRightNowTipShelfDoors(unittest.TestCase):
    def test_right_now_surfaces_four_199_diagnostics(self) -> None:
        raw = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="tip-shelf-199"', raw)
        self.assertIn("$199", raw)
        for sku_id, title, href, cta in DIAGNOSTICS:
            with self.subTest(sku=sku_id):
                self.assertIn(f'id="{sku_id}"', raw)
                self.assertIn(title, raw)
                self.assertIn(f'href="{href}"', raw)
                self.assertIn(cta, raw)
        for plink in FORBIDDEN_PLINKS:
            self.assertNotIn(plink, raw)
        self.assertNotIn("buy.stripe.com", raw)
        self.assertNotIn("donate.stripe.com", raw)


if __name__ == "__main__":
    unittest.main()
