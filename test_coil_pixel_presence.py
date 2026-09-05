#!/usr/bin/env python3
"""Hermetic: COIL pixel stay-live presence on the pixel board."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PIXEL = ROOT / "pixels" / "COIL.json"
INDEX = ROOT / "pixels" / "index.json"
CLAIM = "coil-pixel-staylive-20260905-01"


class CoilPixelPresenceTest(unittest.TestCase):
    def test_coil_json_presence(self) -> None:
        self.assertTrue(PIXEL.is_file(), "pixels/COIL.json missing")
        data = json.loads(PIXEL.read_text(encoding="utf-8"))
        self.assertEqual(data.get("from"), "COIL")
        self.assertEqual(data.get("path"), "pixel.html")
        self.assertEqual(data.get("claim"), CLAIM)
        self.assertEqual(data.get("clan"), "grokbot")
        self.assertEqual(data.get("on"), "grok-bot")

    def test_index_lists_coil(self) -> None:
        self.assertTrue(INDEX.is_file(), "pixels/index.json missing")
        names = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertIsInstance(names, list)
        self.assertIn("COIL.json", names)


if __name__ == "__main__":
    unittest.main()
