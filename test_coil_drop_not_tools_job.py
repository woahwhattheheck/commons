#!/usr/bin/env python3
"""Hermetic: DROP.md keeps Not a TOOLS job section + job/PC cites."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DROP = ROOT / "DROP.md"


class CoilDropNotToolsJobTest(unittest.TestCase):
    def test_section(self) -> None:
        text = DROP.read_text(encoding="utf-8")
        self.assertIn("## Not a TOOLS job", text)
        self.assertIn("job.html", text)
        self.assertIn("muhl_tools_once.py --go", text)
        self.assertIn("tools.json", text)


if __name__ == "__main__":
    unittest.main()
