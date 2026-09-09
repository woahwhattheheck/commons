#!/usr/bin/env python3
"""Hermetic: ground/MANUAL.md keeps Receipt. Dies. law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "ground" / "MANUAL.md"


class CoilGroundManualReceiptDiesTest(unittest.TestCase):
    def test_receipt(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Receipt. Dies", text)


if __name__ == "__main__":
    unittest.main()
