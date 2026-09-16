#!/usr/bin/env python3
"""Hermetic: ground/MANUAL.md Live cash Larger fixed engagements."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "ground" / "MANUAL.md"


class CoilGroundManualLargerFixedTest(unittest.TestCase):
    def test_larger_fixed(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        live = text.split("## Live cash", 1)[1].split("## File a job", 1)[0]
        self.assertIn("Larger fixed engagements", live)
        self.assertIn("diagnostic.html", live)
        self.assertIn("commercial.html", live)


if __name__ == "__main__":
    unittest.main()
