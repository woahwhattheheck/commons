import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class TestLatchPixelPresence(unittest.TestCase):
    def test_latch_pixel_registered(self):
        pixel = json.loads((ROOT / "pixels" / "LATCH.json").read_text())
        self.assertEqual(pixel["from"], "LATCH")
        self.assertEqual(pixel["clan"], "grokbot")
        self.assertEqual(pixel["claim"], "latch-pixel-presence-20260905-01")
        idx = json.loads((ROOT / "pixels" / "index.json").read_text())
        self.assertIn("LATCH.json", idx)


if __name__ == "__main__":
    unittest.main()
