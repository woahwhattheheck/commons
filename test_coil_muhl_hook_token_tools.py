#!/usr/bin/env python3
"""Hermetic: ground/tokens/muhl-hook.md cites TOOLS filing doors."""

from __future__ import annotations

import unittest
from pathlib import Path

DOC = Path(__file__).resolve().parent / "ground" / "tokens" / "muhl-hook.md"


class CoilMuhlHookTokenToolsTest(unittest.TestCase):
    def test_token_tools_doors(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        self.assertIn("job.html", text)
        self.assertIn("manual.html", text)
        self.assertIn("commands.json", text)
        self.assertIn("tools-board", text)
        self.assertIn("harnesses/catalog.json", text)
        self.assertIn("muhl_tools_once.py --go", text)
        self.assertIn("NEED/NONE", text)


if __name__ == "__main__":
    unittest.main()
