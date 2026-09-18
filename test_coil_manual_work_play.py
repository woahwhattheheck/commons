#!/usr/bin/env python3
"""Hermetic: manual.html keeps Work and play same weight."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualWorkPlayTest(unittest.TestCase):
    def test_work_play(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Work and play same weight", text)


if __name__ == "__main__":
    unittest.main()
