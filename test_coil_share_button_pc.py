#!/usr/bin/env python3
"""Hermetic: share.json button is the PC muhl_tools_once --go command."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARE = ROOT / "share.json"
NEEDLE = "muhl_tools_once.py --go"


class CoilShareButtonPcTest(unittest.TestCase):
    def test_button(self) -> None:
        btn = json.loads(SHARE.read_text(encoding="utf-8"))["button"]
        self.assertIsInstance(btn, str)
        self.assertIn(NEEDLE, btn)
        self.assertTrue(btn.strip().startswith("python"))


if __name__ == "__main__":
    unittest.main()
