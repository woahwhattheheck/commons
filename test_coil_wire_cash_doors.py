#!/usr/bin/env python3
"""Hermetic: wire cash doors via wire.html pointer + tools-cash.html shelf."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WIRE = ROOT / "wire.html"
CASH = ROOT / "tools-cash.html"

REQUIRED_CASH = [
    'id="cash-doors"',
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
    "$199 dealer diagnostic",
]


class CoilWireCashDoorsTest(unittest.TestCase):
    def test_wire_points_at_cash_shelf(self) -> None:
        self.assertTrue(WIRE.is_file(), "wire.html missing")
        text = WIRE.read_text(encoding="utf-8")
        self.assertIn('id="cash-doors"', text)
        self.assertIn("./tools-cash.html", text)
        self.assertIn("$29 Autopsy", text)

    def test_tools_cash_page_still_present(self) -> None:
        self.assertTrue(CASH.is_file(), "tools-cash.html missing")
        text = CASH.read_text(encoding="utf-8")
        for needle in REQUIRED_CASH:
            self.assertIn(needle, text, f"missing {needle}")
        # Convert shelf may reuse existing live buys; exact allowlist is
        # test_type_tools_cash_bazaar_convert_shelf_20260917_01.py.


if __name__ == "__main__":
    unittest.main()
