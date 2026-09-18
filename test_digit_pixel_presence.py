#!/usr/bin/env python3
"""Hermetic: DIGIT pixel stay-live presence on the pixel board."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PIXEL = ROOT / "pixels" / "DIGIT.json"
INDEX = ROOT / "pixels" / "index.json"
PRESENCE_CLAIM = "digit-pixel-presence-20260905-01"
STAYLIVE_CLAIM = re.compile(r"^digit-pixel-staylive-\d{8}-\d{2}$")


class DigitPixelPresenceTest(unittest.TestCase):
    def test_digit_json_presence(self) -> None:
        self.assertTrue(PIXEL.is_file(), "pixels/DIGIT.json missing")
        data = json.loads(PIXEL.read_text(encoding="utf-8"))
        self.assertEqual(data.get("from"), "DIGIT")
        self.assertEqual(data.get("path"), "pixel.html")
        claim = data.get("claim")
        self.assertTrue(
            claim == PRESENCE_CLAIM or bool(STAYLIVE_CLAIM.fullmatch(str(claim))),
            "DIGIT claim is neither its first presence nor a stay-live successor",
        )
        self.assertIn(PRESENCE_CLAIM, data.get("src", ""))
        self.assertEqual(data.get("clan"), "grokbot")
        self.assertEqual(data.get("on"), "grok-bot")

    def test_index_lists_digit(self) -> None:
        self.assertTrue(INDEX.is_file(), "pixels/index.json missing")
        names = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertIsInstance(names, list)
        self.assertIn("DIGIT.json", names)


if __name__ == "__main__":
    unittest.main()
