#!/usr/bin/env python3
"""Hermetic: ground/MANUAL.md Living file. Rebuilt from."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "ground" / "MANUAL.md"


class CoilGroundManualLivingFileTest(unittest.TestCase):
    def test_living_file(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Living file. Rebuilt from", text)


if __name__ == "__main__":
    unittest.main()
