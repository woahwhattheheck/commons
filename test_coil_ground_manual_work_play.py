#!/usr/bin/env python3
"""Hermetic: ground/MANUAL.md keeps Work and play same weight."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "ground" / "MANUAL.md"


class CoilGroundManualWorkPlayTest(unittest.TestCase):
    def test_work_play(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Work and play same weight", text)


if __name__ == "__main__":
    unittest.main()
