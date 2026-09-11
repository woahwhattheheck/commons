#!/usr/bin/env python3
"""Hermetic: mcp-conformance.html checkout doors fail closed through pay.js."""
from __future__ import annotations
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "mcp-conformance.html"
CANONICAL_SKUS = {
    "mcp-conformance-receipt-run",
    "mcp-conformance-same-day-repair",
}
REQUIRED = [
    'id="live-cash"',
    "./agent-rescue.html",
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
    "$29 Autopsy",
    "$199 dealer diagnostic",
]


class LatchMcpConformanceLiveCashTest(unittest.TestCase):
    def test_direct_product_doors_use_canonical_fail_closed_slots(self) -> None:
        self.assertTrue(PAGE.is_file())
        text = PAGE.read_text(encoding="utf-8")
        for needle in REQUIRED:
            self.assertIn(needle, text, f"missing {needle}")

        # Static HTML must never bypass the shared capability projector/browser gate.
        stripe = set(re.findall(r"https://(?:buy|donate)\.stripe\.com/[A-Za-z0-9_-]+", text))
        self.assertEqual(stripe, set())
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("donate.stripe.com", text)

        slots = set(re.findall(r'class="js-checkout-slot" data-sku="([^"]+)"', text))
        self.assertEqual(slots, CANONICAL_SKUS)
        self.assertEqual(text.count('class="js-checkout-slot"'), len(CANONICAL_SKUS))
        self.assertIn('<script src="./pay.js?v=20260902a"></script>', text)
        self.assertIn("$49 fixed", text)
        self.assertIn("$250 fixed", text)
        self.assertGreaterEqual(text.count("All sales final."), 2)
        self.assertNotIn("tools-cash.html", text)


if __name__ == "__main__":
    unittest.main()
