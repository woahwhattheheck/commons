#!/usr/bin/env python3
"""Hermetic: manual.html keeps Dest FROM FILE law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualHtmlDestFromFileTest(unittest.TestCase):
    def test_law(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Dest FROM FILE", text)
        self.assertIn("HTTP is not the computer", text)


if __name__ == "__main__":
    unittest.main()
