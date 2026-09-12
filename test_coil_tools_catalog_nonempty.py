#!/usr/bin/env python3
"""Hermetic: tools.json tools catalog nonempty with unique ids."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsCatalogNonemptyTest(unittest.TestCase):
    def test_catalog_shape(self) -> None:
        tools = json.loads(TOOLS.read_text(encoding="utf-8"))["tools"]
        self.assertIsInstance(tools, list)
        self.assertGreaterEqual(len(tools), 10)
        ids = []
        for t in tools:
            self.assertIn("id", t)
            self.assertIn("group", t)
            self.assertIn("label", t)
            self.assertTrue(t["id"])
            ids.append(t["id"])
        self.assertEqual(len(ids), len(set(ids)), "duplicate tool id")


if __name__ == "__main__":
    unittest.main()
