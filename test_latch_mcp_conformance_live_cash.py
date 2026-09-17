#!/usr/bin/env python3
"""Hermetic: MCP Conformance live-cash pointers plus verified static checkout.

GOAT convert leftover `goat-mcp-conformance-checkout-wire-20260917-01`
wires the existing livemode Payment Links as static/noscript CTAs so checkout
does not wait on catalog hydration. Live-cash Autopsy/$199 pointers stay.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "mcp-conformance.html"
RECEIPT_RUN = "https://buy.stripe.com/fZudR8bgV637fT3ctc43S0r"
SAME_DAY = "https://buy.stripe.com/14AeVcgBf2QV5epbp843S0s"
REQUIRED = [
    'id="live-cash"',
    "./agent-rescue.html",
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
    "$29 Autopsy",
    "$199 dealer diagnostic",
    RECEIPT_RUN,
    SAME_DAY,
    "Start the $49 receipt run",
    "Start the $250 same-day repair",
    "<noscript>",
]


class LatchMcpConformanceLiveCashTest(unittest.TestCase):
    def test_direct_product_doors(self) -> None:
        self.assertTrue(PAGE.is_file())
        text = PAGE.read_text(encoding="utf-8")
        for needle in REQUIRED:
            self.assertIn(needle, text, f"missing {needle}")
        noscript = text.split("<noscript>", 1)[1].split("</noscript>", 1)[0]
        self.assertIn(RECEIPT_RUN, noscript)
        self.assertIn(SAME_DAY, noscript)
        self.assertNotIn('class="js-checkout-slot"', text)
        self.assertNotIn("pay.js", text)
        self.assertNotIn("donate.stripe.com", text)
        self.assertGreaterEqual(text.count("All sales final."), 2)
        self.assertNotIn("tools-cash.html", text)


if __name__ == "__main__":
    unittest.main()
