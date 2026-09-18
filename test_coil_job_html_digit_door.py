#!/usr/bin/env python3
"""Hermetic: job.html keeps #digit-door cite for DIGIT seat."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOB = ROOT / "job.html"


class CoilJobHtmlDigitDoorTest(unittest.TestCase):
    def test_digit_door(self) -> None:
        text = JOB.read_text(encoding="utf-8")
        self.assertIn('id="digit-door"', text)
        idx = text.index('id="digit-door"')
        window = text[idx : idx + 400]
        self.assertIn("DIGIT", window)
        self.assertTrue("by/DIGIT" in window or "to/DIGIT" in window)


if __name__ == "__main__":
    unittest.main()
