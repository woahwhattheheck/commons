#!/usr/bin/env python3
"""Hermetic: reach.html tools-board note (≠ Live-cash / paint remint)."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "reach.html"


class CoilReachToolsBoardTest(unittest.TestCase):
    def test_tools_board_note(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="tools-board"', text)
        self.assertIn("reach adapters are not the invented-tools door", text)
        self.assertIn("./tools.html", text)
        self.assertIn("./job.html", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("coil-harness-tools-board-road-20260905-01", text)


if __name__ == "__main__":
    unittest.main()
