#!/usr/bin/env python3
"""Hermetic: wakeup.html keeps Universal door + tools-jobs cite."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wakeup.html"


class CoilWakeupUniversalDoorTest(unittest.TestCase):
    def test_door(self) -> None:
        text = WAKE.read_text(encoding="utf-8")
        self.assertTrue("Universal" in text or "universal" in text.lower())
        self.assertIn('id="tools-jobs"', text)
        self.assertIn("job.html", text)


if __name__ == "__main__":
    unittest.main()
