#!/usr/bin/env python3
"""Hermetic: boards.html cites tools.html (nav only)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BOARDS = ROOT / "boards.html"


class CoilBoardsToolsNavTest(unittest.TestCase):
    def test_nav(self) -> None:
        text = BOARDS.read_text(encoding="utf-8")
        self.assertIn("tools.html", text)


if __name__ == "__main__":
    unittest.main()
