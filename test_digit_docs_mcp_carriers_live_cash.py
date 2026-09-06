#!/usr/bin/env python3
"""Hermetic: docs/mcp-carriers.md Live cash section."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOC = ROOT / "docs" / "mcp-carriers.md"

REQUIRED = [
    "## Live cash",
    "../agent-rescue.html",
    "../dealer-service-lead-rescue.html",
    "../referral-intake-completeness.html",
    "../repair-booking-preflight.html",
    "../plant-downtime-handoff.html",
    "$29 Autopsy",
    "$199 dealer diagnostic",
]


class DigitDocsMcpCarriersLiveCashTest(unittest.TestCase):
    def test_live_cash_section(self) -> None:
        self.assertTrue(DOC.is_file(), "docs/mcp-carriers.md missing")
        text = DOC.read_text(encoding="utf-8")
        for needle in REQUIRED:
            self.assertIn(needle, text, f"missing {needle}")
        self.assertNotIn("buy.stripe.com", text)
        self.assertLess(text.index("## Live cash"), text.index("## Shared handshake"))


if __name__ == "__main__":
    unittest.main()
