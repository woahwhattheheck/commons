#!/usr/bin/env python3
"""Hermetic: muhl_tools_once NEED cites board doors (≠ paint remint)."""

from __future__ import annotations

import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent / "host" / "muhl_tools_once.py"


class CoilMuhlToolsOnceNeedBoardTest(unittest.TestCase):
    def test_need_board_lines(self) -> None:
        text = SRC.read_text(encoding="utf-8")
        self.assertIn('print("NEED — python host/muhl_tools_once.py --go")', text)
        self.assertIn('print("File jobs: job.html · catalog: tools.json · board: tools.html")', text)
        self.assertIn('print("Harness road: tools-board (harnesses/catalog.json).")', text)
        # still one-job die semantics
        self.assertIn('print("ONE job. then die. not a poller.")', text)
        self.assertIn('print("DIE")', text)


if __name__ == "__main__":
    unittest.main()
