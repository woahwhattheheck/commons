#!/usr/bin/env python3
"""Hermetic: tools.html keeps Check the board often cue."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"


class CoilToolsHtmlCheckTheBoardTest(unittest.TestCase):
    def test_check(self) -> None:
        text = TOOLS.read_text(encoding="utf-8")
        self.assertIn("Check the board often", text)
        self.assertIn("updates by the second", text)


if __name__ == "__main__":
    unittest.main()
