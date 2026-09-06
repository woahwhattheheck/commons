#!/usr/bin/env python3
"""Hermetic: DROP.md Not a TOOLS job section."""

from __future__ import annotations

import unittest
from pathlib import Path

DOC = Path(__file__).resolve().parent / "DROP.md"


class CoilDropVsToolsTest(unittest.TestCase):
    def test_not_a_tools_job(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        section = text.split("## Not a TOOLS job", 1)[1].split("## Before you drop", 1)[0]
        self.assertIn("job.html", section)
        self.assertIn("tools.json", section)
        self.assertIn("tools.html", section)
        self.assertIn("muhl_tools_once.py --go", section)
        self.assertIn("muhl-hook", section)
        self.assertLess(text.index("## Not a TOOLS job"), text.index("## Before you drop"))


if __name__ == "__main__":
    unittest.main()
