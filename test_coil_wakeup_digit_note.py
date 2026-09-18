#!/usr/bin/env python3
"""Hermetic: wakeup.html keeps DIGIT seat note."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wakeup.html"


class CoilWakeupDigitNoteTest(unittest.TestCase):
    def test_note(self) -> None:
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn('id="digit-note"', text)
        self.assertIn("DIGIT", text)
        self.assertIn("clan/grokbot", text)


if __name__ == "__main__":
    unittest.main()
