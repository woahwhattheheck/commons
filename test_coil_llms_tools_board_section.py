#!/usr/bin/env python3
"""Hermetic: llms.txt keeps ## Tools board with job/PC cites."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LLMS = ROOT / "llms.txt"


class CoilLlmsToolsBoardSectionTest(unittest.TestCase):
    def test_section(self) -> None:
        text = LLMS.read_text(encoding="utf-8")
        self.assertIn("## Tools board", text)
        idx = text.index("## Tools board")
        # until next ## or end
        rest = text[idx + 2 :]
        end = rest.find("\n## ")
        section = rest if end < 0 else rest[:end]
        self.assertIn("job.html", section)
        self.assertIn("muhl_tools_once.py --go", section)
        self.assertIn("tools.json", section)


if __name__ == "__main__":
    unittest.main()
