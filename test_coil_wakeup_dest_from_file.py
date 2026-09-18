#!/usr/bin/env python3
"""Hermetic: wakeup.html keeps Dest FROM FILE law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wakeup.html"


class CoilWakeupDestFromFileTest(unittest.TestCase):
    def test_law(self) -> None:
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn("Dest FROM FILE", text)
        self.assertIn("HTTP is not the computer", text)


if __name__ == "__main__":
    unittest.main()
