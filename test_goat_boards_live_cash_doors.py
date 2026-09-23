#!/usr/bin/env python3
"""Hermetic: boards.html surfaces live diagnostic cash doors (product pages only)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "boards.html"

DOORS = (
    ("sku-dealer-service-lead-rescue", "./dealer-service-lead-rescue.html", "Open $199 dealer diagnostic"),
    ("sku-referral-intake-completeness", "./referral-intake-completeness.html", "Open $199 referral diagnostic"),
    ("sku-repair-booking-preflight", "./repair-booking-preflight.html", "Open $199 repair diagnostic"),
    ("sku-plant-downtime-handoff", "./plant-downtime-handoff.html", "Open $199 plant diagnostic"),
)


class TestGoatBoardsLiveCashDoors(unittest.TestCase):
    def test_boards_surfaces_live_diagnostic_doors(self) -> None:
        raw = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="live-cash-doors"', raw)
        start = raw.index('id="live-cash-doors"')
        end = raw.index("</section>", start)
        section = raw[start:end]
        for sku_id, href, cta in DOORS:
            with self.subTest(sku=sku_id):
                self.assertIn(f'id="{sku_id}"', section)
                self.assertIn(f'href="{href}"', section)
                self.assertIn(cta, section)
        self.assertNotIn("buy.stripe.com", section)
        self.assertNotIn("donate.stripe.com", section)
        self.assertNotIn("agent-rescue.html", section)
        self.assertNotIn("sku-agent-failure-autopsy", section)

    def test_hub_pages_rebuild_keeps_live_cash_doors(self) -> None:
        src = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertIn('id="live-cash-doors"', src)
        self.assertNotIn('id="sku-agent-failure-autopsy"', src)
        self.assertNotIn("agent-rescue.html", src)


if __name__ == "__main__":
    unittest.main()
