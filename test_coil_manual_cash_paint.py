#!/usr/bin/env python3
"""Hermetic: manual.html paints tools.json cash into #cash-hook."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "manual.html"


class CoilManualCashPaintTest(unittest.TestCase):
    def test_cash_hook_paint(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="cash-hook"', text)
        self.assertIn("data.cash", text)
        self.assertIn("cash-hook", text)
        self.assertIn("Catalog cash (tools.json", text)
        self.assertIn("cash.shelf", text)
        self.assertIn("cash.doors", text)


if __name__ == "__main__":
    unittest.main()
