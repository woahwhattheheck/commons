"""Hermetic: court.html dropped void 337 ritual; smash warning kept."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
class TestAdminCourtDrop337No(unittest.TestCase):
    def test_no_fire_337_ritual(self):
        text = (ROOT / "court.html").read_text(encoding="utf-8")
        self.assertNotIn("Do not fire 337", text)
        self.assertIn("Do not smash commons.mno", text)
if __name__ == "__main__":
    unittest.main()
