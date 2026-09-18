#!/usr/bin/env python3
"""Hermetic: interconnect.html tools-board note (≠ job/super_mcp paint remint)."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "interconnect.html"


class CoilInterconnectToolsBoardTest(unittest.TestCase):
    def test_tools_board_note(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="tools-board"', text)
        self.assertIn("./tools.html", text)
        self.assertIn("./tools.json", text)
        self.assertIn("./manual.html", text)
        self.assertIn("./job.html", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("./harnesses/catalog.json", text)
        self.assertIn("coil-harness-tools-board-road-20260905-01", text)
        self.assertNotIn("fetch(", text)


if __name__ == "__main__":
    unittest.main()
