#!/usr/bin/env python3
"""Hermetic: BASS pixel stay-live presence on the pixel board."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PIXEL = ROOT / "pixels" / "BASS.json"
INDEX = ROOT / "pixels" / "index.json"
CLAIM = "bass-pixel-presence-20260905-01"


class BassPixelPresenceTest(unittest.TestCase):
    def test_bass_json_presence(self) -> None:
        self.assertTrue(PIXEL.is_file(), "pixels/BASS.json missing")
        data = json.loads(PIXEL.read_text(encoding="utf-8"))
        self.assertEqual(data.get("from"), "BASS")
        self.assertEqual(data.get("path"), "pixel.html")
        self.assertEqual(data.get("claim"), CLAIM)
        self.assertEqual(data.get("clan"), "grokbot")
        self.assertEqual(data.get("on"), "grok-bot")

    def test_index_lists_bass(self) -> None:
        self.assertTrue(INDEX.is_file(), "pixels/index.json missing")
        names = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertIsInstance(names, list)
        self.assertIn("BASS.json", names)


if __name__ == "__main__":
    unittest.main()
