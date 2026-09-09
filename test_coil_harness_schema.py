#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json schema + version + roads.tools-board."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [
    ROOT / "harnesses" / "catalog.json",
    ROOT / "catalog.json",
]


class CoilHarnessSchemaTest(unittest.TestCase):
    def test_schema(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "commons-cross-harness-capabilities/v1")
        self.assertRegex(data["version"], r"^\d+\.\d+\.\d+$")
        self.assertIsInstance(data["roads"], dict)
        self.assertIn("tools-board", data["roads"])
        self.assertIsInstance(data.get("harnesses"), (dict, list))


if __name__ == "__main__":
    unittest.main()
