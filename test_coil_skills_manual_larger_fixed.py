#!/usr/bin/env python3
"""Hermetic: skills/MANUAL.md Live cash Larger fixed."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "skills" / "MANUAL.md"


class CoilSkillsManualLargerFixedTest(unittest.TestCase):
    def test_larger_fixed(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        live = text.split("## Live cash", 1)[1].split("| if your job is", 1)[0]
        self.assertIn("Larger fixed engagements", live)
        self.assertIn("diagnostic.html", live)
        self.assertIn("commercial.html", live)


if __name__ == "__main__":
    unittest.main()
