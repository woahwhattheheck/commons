#!/usr/bin/env python3
"""Hermetic: ground/MANUAL.md cites PC button host/muhl_tools_once.py --go."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "ground" / "MANUAL.md"


class CoilGroundManualPcTest(unittest.TestCase):
    def test_pc(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("tools.html", text)


if __name__ == "__main__":
    unittest.main()
