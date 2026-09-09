#!/usr/bin/env python3
"""Hermetic: muhl_tools_once NONE path cites board doors (≠ NEED remint alone)."""

from __future__ import annotations

import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent / "host" / "muhl_tools_once.py"


class CoilMuhlToolsOnceNoneBoardTest(unittest.TestCase):
    def test_none_board_lines(self) -> None:
        text = SRC.read_text(encoding="utf-8")
        self.assertIn('print("NONE — no open TOOLS job")', text)
        self.assertIn('print("File one at job.html · catalog: tools.json · board: tools.html")', text)
        self.assertIn('print("Then: python host/muhl_tools_once.py --go")', text)
        # NEED path still present
        self.assertIn('print("NEED — python host/muhl_tools_once.py --go")', text)


if __name__ == "__main__":
    unittest.main()
