#!/usr/bin/env python3
"""Hermetic: manual.html keeps Drive Bryce invented tools cue."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualHtmlDriveBryceTest(unittest.TestCase):
    def test_drive(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Bryce invented", text)
        self.assertIn("Drive them from the board", text)


if __name__ == "__main__":
    unittest.main()
