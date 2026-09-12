#!/usr/bin/env python3
"""Hermetic: tools.html keeps HTTP is not the computer."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"


class CoilToolsHtmlHttpNotComputerTest(unittest.TestCase):
    def test_law(self) -> None:
        text = TOOLS.read_text(encoding="utf-8")
        self.assertIn("HTTP is not the computer", text)


if __name__ == "__main__":
    unittest.main()
