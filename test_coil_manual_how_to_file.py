#!/usr/bin/env python3
"""Hermetic: manual.html How to file a job."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualHowToFileTest(unittest.TestCase):
    def test_how_to_file(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("How to file a job", text)


if __name__ == "__main__":
    unittest.main()
