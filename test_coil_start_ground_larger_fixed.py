#!/usr/bin/env python3
"""Hermetic: START + ground Live cash cite Larger fixed product doors."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
NEEDLE = "Larger fixed engagements"
HREFS_ROOT = ("./diagnostic.html", "./commercial.html")
HREFS_GROUND = ("../diagnostic.html", "../commercial.html")


class CoilStartGroundLargerFixed(unittest.TestCase):
    def test_start_and_agents(self):
        for name in ("START.md", "AGENTS.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn(NEEDLE, text)
            self.assertIn("$12,000", text)
            self.assertIn("$30,000", text)
            for href in HREFS_ROOT:
                self.assertIn(href, text)

    def test_ground_doors(self):
        for name in ("HEAD.md", "PICK.md", "CURSOR.md", "SLACK.md"):
            text = (ROOT / "ground" / name).read_text(encoding="utf-8")
            self.assertIn(NEEDLE, text)
            for href in HREFS_GROUND:
                self.assertIn(href, text)


if __name__ == "__main__":
    unittest.main()
