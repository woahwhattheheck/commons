#!/usr/bin/env python3
"""Hermetic: commercial.html has catalog cash hook."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "commercial.html"


class CoilCommercialCashHookTest(unittest.TestCase):
    def test_cash_hook(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="cash-hook"', text)
        self.assertIn("./tools.json", text)
        self.assertIn("./tools-cash.html", text)
        self.assertIn("coil-tools-json-live-cash-20260905-01", text)


if __name__ == "__main__":
    unittest.main()
