#!/usr/bin/env python3
"""Hermetic: manual.html keeps Receipt. Dies. law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualReceiptDiesTest(unittest.TestCase):
    def test_receipt(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Receipt. Dies", text)


if __name__ == "__main__":
    unittest.main()
