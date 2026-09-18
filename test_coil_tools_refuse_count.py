#!/usr/bin/env python3
"""Hermetic: tools.json refuse[] has at least 8 unique entries."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsRefuseCountTest(unittest.TestCase):
    def test_count(self) -> None:
        refuse = json.loads(TOOLS.read_text(encoding="utf-8"))["refuse"]
        self.assertIsInstance(refuse, list)
        self.assertGreaterEqual(len(refuse), 8)
        self.assertEqual(len(refuse), len(set(refuse)))


if __name__ == "__main__":
    unittest.main()
