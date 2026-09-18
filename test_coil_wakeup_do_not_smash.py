#!/usr/bin/env python3
"""Hermetic: wakeup.html keeps Do not smash commons.mno law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wakeup.html"


class CoilWakeupDoNotSmashTest(unittest.TestCase):
    def test_smash(self) -> None:
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn("Do not smash commons.mno", text)


if __name__ == "__main__":
    unittest.main()
