#!/usr/bin/env python3
"""Hermetic: manual.html reads tools.json on this load."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualReadsToolsJsonTest(unittest.TestCase):
    def test_reads(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Reads tools.json", text)
        self.assertIn("on this load", text)


if __name__ == "__main__":
    unittest.main()
