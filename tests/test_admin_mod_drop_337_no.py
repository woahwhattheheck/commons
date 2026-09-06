"""Hermetic: mod.html dropped void 337 ritual; smash warning kept."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestAdminModDrop337No(unittest.TestCase):
    def test_no_fire_337_ritual(self):
        text = (ROOT / "mod.html").read_text(encoding="utf-8")
        self.assertNotIn("Do not fire 337", text)
        self.assertNotIn("Do not fire 337.", text)
        # smash warning remains
        self.assertIn("Do not smash commons.mno", text)
        self.assertIn("HTTP is not the computer", text)


if __name__ == "__main__":
    unittest.main()
