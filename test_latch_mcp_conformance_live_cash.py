#!/usr/bin/env python3
"""Hermetic: mcp-conformance.html Live cash — tip-shelf product doors."""
from __future__ import annotations
import re
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "mcp-conformance.html"
# The only Stripe URLs allowed on the page: the two canonical MCP rails in
# revenue/checkout_capability/snapshot.json.
CANONICAL_CHECKOUTS = {
    "https://buy.stripe.com/fZudR8bgV637fT3ctc43S0r",
    "https://buy.stripe.com/14AeVcgBf2QV5epbp843S0s",
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
    def test_direct_product_doors(self) -> None:
        self.assertTrue(PAGE.is_file())
        text = PAGE.read_text(encoding="utf-8")
        for needle in REQUIRED:
            self.assertIn(needle, text, f"missing {needle}")
        stripe = set(re.findall(r"https://buy\.stripe\.com/[A-Za-z0-9_-]+", text))
        self.assertEqual(stripe, CANONICAL_CHECKOUTS)
        self.assertEqual(text.count("buy.stripe.com"), len(CANONICAL_CHECKOUTS))
        self.assertNotIn("tools-cash.html", text)
if __name__ == "__main__":
    unittest.main()
