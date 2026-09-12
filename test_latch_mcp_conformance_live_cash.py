#!/usr/bin/env python3
"""Hermetic: MCP Conformance checkout routes delegate to the shared fail-closed gate."""
from __future__ import annotations
import re
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "mcp-conformance.html"
CHECKOUT_SKUS = (
    "mcp-conformance-receipt-run",
    "mcp-conformance-same-day-repair",
)
REQUIRED = [
    'id="live-cash"',
    "./agent-rescue.html",
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
    "$29 Autopsy",
    "$199 dealer diagnostic",
    '<script src="./pay.js?v=20260902a"></script>',
]
class LatchMcpConformanceLiveCashTest(unittest.TestCase):
    def test_direct_product_doors(self) -> None:
        self.assertTrue(PAGE.is_file())
        text = PAGE.read_text(encoding="utf-8")
        for needle in REQUIRED:
            self.assertIn(needle, text, f"missing {needle}")
        # Provider URLs must never be static page authority. pay.js renders a
        # checkout only after the canonical account + rail + catalog gates pass.
        stripe = set(re.findall(r"https://(?:buy|donate)\.stripe\.com/[A-Za-z0-9_-]+", text))
        self.assertEqual(stripe, set())
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("donate.stripe.com", text)
        self.assertEqual(text.count('class="js-checkout-slot"'), len(CHECKOUT_SKUS))
        for sku in CHECKOUT_SKUS:
            self.assertEqual(text.count(f'data-sku="{sku}"'), 1)
        self.assertGreaterEqual(text.count("All sales final."), len(CHECKOUT_SKUS))
        self.assertNotIn("tools-cash.html", text)
if __name__ == "__main__":
    unittest.main()
