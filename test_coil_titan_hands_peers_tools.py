#!/usr/bin/env python3
"""Hermetic: docs/TITAN_HANDS_PEERS.md Tools board section (≠ HTML-note remint)."""

from __future__ import annotations

import unittest
from pathlib import Path

DOC = Path(__file__).resolve().parent / "docs" / "TITAN_HANDS_PEERS.md"


class CoilTitanHandsPeersToolsTest(unittest.TestCase):
    def test_tools_board_section(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        section = text.split("## Tools board (invented tools)", 1)[1].split("## Carrier matrix", 1)[0]
        self.assertIn("../tools.html", section)
        self.assertIn("../tools.json", section)
        self.assertIn("../job.html", section)
        self.assertIn("python host/muhl_tools_once.py --go", section)
        self.assertIn("../harnesses/catalog.json", section)
        self.assertIn("coil-harness-tools-board-road-20260905-01", section)
        self.assertLess(
            text.index("## Tools board (invented tools)"),
            text.index("## Carrier matrix"),
        )


if __name__ == "__main__":
    unittest.main()
