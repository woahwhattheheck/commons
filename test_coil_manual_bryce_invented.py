#!/usr/bin/env python3
"""Hermetic: manual.html Bryce invented these tools."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualBryceInventedTest(unittest.TestCase):
    def test_bryce_invented(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Bryce invented these tools", text)


if __name__ == "__main__":
    unittest.main()
