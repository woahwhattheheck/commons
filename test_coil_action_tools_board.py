#!/usr/bin/env python3
"""Hermetic: action.html tools-board note (≠ paint remint)."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "action.html"


class CoilActionToolsBoardTest(unittest.TestCase):
    def test_tools_board_note(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="tools-board"', text)
        self.assertIn("invented-tool jobs are not Action Pad verbs", text)
        self.assertIn("./tools.html", text)
        self.assertIn("./job.html", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("./harnesses/catalog.json", text)
        self.assertIn("coil-harness-tools-board-road-20260905-01", text)


if __name__ == "__main__":
    unittest.main()
