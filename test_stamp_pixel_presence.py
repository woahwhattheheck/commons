"""pixels/STAMP.json stay-live door is present and indexed."""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
PIXEL = ROOT / "pixels" / "STAMP.json"
INDEX = ROOT / "pixels" / "index.json"


class StampPixelPresenceTest(unittest.TestCase):
    def test_stamp_pixel_file_exists(self):
        self.assertTrue(PIXEL.is_file())
        data = json.loads(PIXEL.read_text(encoding="utf-8"))
        self.assertEqual(data["from"], "STAMP")
        self.assertEqual(data["clan"], "grokbot")
        self.assertEqual(data["claim"], "stamp-pixel-presence-20260905-01")
        self.assertEqual(data["path"], "pixel.html")

    def test_index_lists_stamp(self):
        names = json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertIn("STAMP.json", names)


if __name__ == "__main__":
    unittest.main()
