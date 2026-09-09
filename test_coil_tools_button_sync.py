#!/usr/bin/env python3
"""Hermetic: tools.json button == share.json button (PC command drift lock)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
SHARE = ROOT / "share.json"
EXPECTED = "python host/muhl_tools_once.py --go"


class CoilToolsButtonSyncTest(unittest.TestCase):
    def test_buttons_match(self) -> None:
        self.assertTrue(TOOLS.is_file(), "tools.json missing")
        self.assertTrue(SHARE.is_file(), "share.json missing")
        tools_btn = json.loads(TOOLS.read_text(encoding="utf-8")).get("button")
        share_btn = json.loads(SHARE.read_text(encoding="utf-8")).get("button")
        self.assertEqual(tools_btn, EXPECTED)
        self.assertEqual(share_btn, EXPECTED)
        self.assertEqual(tools_btn, share_btn, "tools.json button drifted from share.json button")


if __name__ == "__main__":
    unittest.main()
