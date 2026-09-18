#!/usr/bin/env python3
"""Hermetic: manual.html keeps Living manual / bake-not-catalog law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualLivingManualTest(unittest.TestCase):
    def test_living(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Living manual", text)
        self.assertIn("A bake is not the catalog", text)


if __name__ == "__main__":
    unittest.main()
