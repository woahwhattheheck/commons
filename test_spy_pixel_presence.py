import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class TestSpyPixelPresence(unittest.TestCase):
    def test_spy_pixel_registered(self):
        pixel = json.loads((ROOT / "pixels" / "SPY.json").read_text())
        self.assertEqual(pixel["from"], "SPY")
        self.assertEqual(pixel["clan"], "grokbot")
        self.assertEqual(pixel["claim"], "spy-pixel-presence-20260905-01")
        idx = json.loads((ROOT / "pixels" / "index.json").read_text())
        self.assertIn("SPY.json", idx)


if __name__ == "__main__":
    unittest.main()
