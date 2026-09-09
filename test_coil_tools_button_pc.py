#!/usr/bin/env python3
"""Hermetic: tools.json button is the PC muhl_tools_once --go command."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
NEEDLE = "muhl_tools_once.py --go"


class CoilToolsButtonPcTest(unittest.TestCase):
    def test_button_pc(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        btn = data["button"]
        self.assertIsInstance(btn, str)
        self.assertIn(NEEDLE, btn)
        self.assertTrue(btn.strip().startswith("python"))


if __name__ == "__main__":
    unittest.main()
