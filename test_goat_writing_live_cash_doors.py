#!/usr/bin/env python3
"""Hermetic: writing.html surfaces live diagnostic cash doors (product pages only).

CONVERT MONEY SHIP reuses two existing live buy.stripe.com Payment Links on
the first-screen convert shelf. Those URLs stay out of #live-cash and
#live-cash-doors. Do not invent donate.stripe.com. Cite
latch-writing-cweather-convert-shelf-20260917-01 ·
goat-tips-live-cash-doors-20260905-01 — do not remint.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "writing.html"

DOORS = (
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
        live_cash = raw.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
        doors = raw.split('id="live-cash-doors"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", live_cash)
        self.assertNotIn("buy.stripe.com", doors)
        self.assertNotIn("donate.stripe.com", raw)


if __name__ == "__main__":
    unittest.main()
