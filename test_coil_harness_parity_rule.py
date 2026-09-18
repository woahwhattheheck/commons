#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json parity_rule nonempty + discover cite."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessParityRuleTest(unittest.TestCase):
    def test_parity(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        rule = data["parity_rule"]
        self.assertIsInstance(rule, str)
        self.assertTrue(rule.strip())
        low = rule.lower()
        self.assertIn("discover", low)
        self.assertIn("road", low)


if __name__ == "__main__":
    unittest.main()
