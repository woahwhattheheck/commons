#!/usr/bin/env python3
"""Hermetic: llms.txt has Tools board section with job.html."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "llms.txt"


class CoilLlmsToolsBoardTest(unittest.TestCase):
    def test_tools_board_section(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("## Tools board", text)
        self.assertIn("job.html", text)
        self.assertIn("tools.json", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("tools-board", text)
        self.assertIn("Dest FROM FILE", text)


if __name__ == "__main__":
    unittest.main()
