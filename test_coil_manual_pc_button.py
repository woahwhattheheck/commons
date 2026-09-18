#!/usr/bin/env python3
"""Hermetic: manual.html cites PC button host/muhl_tools_once.py --go."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualPcButtonTest(unittest.TestCase):
    def test_pc_button(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("PC button", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("tools.json", text)


if __name__ == "__main__":
    unittest.main()
