#!/usr/bin/env python3
"""Hermetic: super-mcp.html Live cash — direct product doors (not tools-cash pointer)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "super-mcp.html"

REQUIRED = [
    'id="live-cash"',
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
    "$199 dealer diagnostic",
]


class CoilSuperMcpLiveCashTest(unittest.TestCase):
    def test_direct_product_doors(self) -> None:
        self.assertTrue(PAGE.is_file(), "super-mcp.html missing")
        text = PAGE.read_text(encoding="utf-8")
        for needle in REQUIRED:
            self.assertIn(needle, text, f"missing {needle}")
        self.assertNotIn("buy.stripe.com", text.split('id="live-cash"', 1)[1].split('</section>', 1)[0])
        self.assertNotIn("tools-cash.html", text)


if __name__ == "__main__":
    unittest.main()
