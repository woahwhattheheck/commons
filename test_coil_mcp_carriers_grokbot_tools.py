#!/usr/bin/env python3
"""Hermetic: docs/mcp-carriers.md Grok Bot tools board pointer (≠ job-hook remint)."""

from __future__ import annotations

import unittest
from pathlib import Path

DOC = Path(__file__).resolve().parent / "docs" / "mcp-carriers.md"


class CoilMcpCarriersGrokbotToolsTest(unittest.TestCase):
    def test_grokbot_tools_board_pointer(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        section = text.split("## Grok Bot (Grokbot)", 1)[1].split("## TITAN Hands", 1)[0]
        self.assertIn("Tools board (Commons)", section)
        self.assertIn("../tools.html", section)
        self.assertIn("../tools.json", section)
        self.assertIn("../manual.html", section)
        self.assertIn("../job.html", section)
        self.assertIn("python host/muhl_tools_once.py --go", section)
        self.assertIn("Coil door: TOOLS", section)


if __name__ == "__main__":
    unittest.main()
