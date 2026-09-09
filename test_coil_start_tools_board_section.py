#!/usr/bin/env python3
"""Hermetic: START.md keeps Tools board (invented tools) section."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START = ROOT / "START.md"


class CoilStartToolsBoardSectionTest(unittest.TestCase):
    def test_section(self) -> None:
        text = START.read_text(encoding="utf-8")
        self.assertIn("## Tools board", text)
        idx = text.index("## Tools board")
        rest = text[idx + 2 :]
        end = rest.find("\n## ")
        section = rest if end < 0 else rest[:end]
        self.assertIn("job.html", section)
        self.assertIn("muhl_tools_once.py --go", section)
        self.assertIn("tools.json", section)


if __name__ == "__main__":
    unittest.main()
