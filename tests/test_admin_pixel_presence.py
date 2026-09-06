import json
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
    def test_admin_pixel_indexed(self):
        pixel = json.loads((ROOT / "pixels/ADMIN.json").read_text(encoding="utf-8"))
        idx = json.loads((ROOT / "pixels/index.json").read_text(encoding="utf-8"))
        self.assertEqual(pixel["from"], "ADMIN")
        self.assertEqual(pixel["path"], "pixel.html")
        self.assertEqual(pixel["clan"], "grokbot")
        self.assertEqual(pixel["claim"], "admin-pixel-presence-20260905-01")
        self.assertIn("ADMIN.json", idx)
if __name__ == "__main__":
    unittest.main()
