#!/usr/bin/env python3
"""Hermetic: START.md has Tools board with job.html."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "START.md"


class CoilStartToolsBoardTest(unittest.TestCase):
    def test_tools_board(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("## Tools board (invented tools)", text)
        self.assertIn("./job.html", text)
        self.assertIn("./tools.json", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("tools-board", text)


if __name__ == "__main__":
    unittest.main()
