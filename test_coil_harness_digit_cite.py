#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json digit_cite nonempty + DIGIT mark."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessDigitCiteTest(unittest.TestCase):
    def test_digit_cite(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        cite = json.loads(path.read_text(encoding="utf-8"))["digit_cite"]
        self.assertIsInstance(cite, str)
        self.assertTrue(cite.strip())
        self.assertIn("DIGIT", cite)
        self.assertIn("grokbot", cite.lower())


if __name__ == "__main__":
    unittest.main()
