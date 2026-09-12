#!/usr/bin/env python3
"""Hermetic: ground/MANUAL.md HTML that cannot go stale."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "ground" / "MANUAL.md"


class CoilGroundManualCannotGoStaleTest(unittest.TestCase):
    def test_cannot_go_stale(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("HTML that cannot go stale", text)


if __name__ == "__main__":
    unittest.main()
