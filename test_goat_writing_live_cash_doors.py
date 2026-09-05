#!/usr/bin/env python3
"""Hermetic: writing.html surfaces live diagnostic cash doors (product pages only)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "writing.html"

DOORS = (
    ("sku-agent-failure-autopsy", "./agent-rescue.html", "Open $29 Autopsy checkout"),
    ("sku-dealer-service-lead-rescue", "./dealer-service-lead-rescue.html", "Open $199 dealer diagnostic"),
    ("sku-referral-intake-completeness", "./referral-intake-completeness.html", "Open $199 referral diagnostic"),
    ("sku-repair-booking-preflight", "./repair-booking-preflight.html", "Open $199 repair diagnostic"),
    ("sku-plant-downtime-handoff", "./plant-downtime-handoff.html", "Open $199 plant diagnostic"),
)


class TestGoatWritingLiveCashDoors(unittest.TestCase):
    def test_writing_surfaces_live_diagnostic_doors(self) -> None:
        raw = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="live-cash-doors"', raw)
        for sku_id, href, cta in DOORS:
            with self.subTest(sku=sku_id):
                self.assertIn(f'id="{sku_id}"', raw)
                self.assertIn(f'href="{href}"', raw)
                self.assertIn(cta, raw)
        self.assertNotIn("buy.stripe.com", raw)
        self.assertNotIn("donate.stripe.com", raw)


if __name__ == "__main__":
    unittest.main()
