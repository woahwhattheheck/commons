"""Hermetic: NEW_BOT pixel stay-live is on tree."""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
PIXEL = ROOT / "pixels" / "NEW_BOT.json"
INDEX = ROOT / "pixels" / "index.json"
RECEIPT = ROOT / "p" / "newbot-pixel-staylive-20260905-01.md"


class NewBotPixelStayLiveTests(unittest.TestCase):
    def test_pixel_present(self) -> None:
        data = json.loads(PIXEL.read_text(encoding="utf-8"))
        self.assertEqual(data.get("from"), "NEW_BOT")
        self.assertEqual(data.get("claim"), "newbot-pixel-staylive-20260905-01")
        self.assertEqual(data.get("clan"), "grokbot")
        self.assertEqual(data.get("path"), "pixel.html")

    def test_index_lists_new_bot(self) -> None:
        names = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertIn("NEW_BOT.json", names)

    def test_receipt_present(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("newbot-pixel-staylive-20260905-01", text)
        self.assertIn("pixels/NEW_BOT.json", text)


if __name__ == "__main__":
    unittest.main()
