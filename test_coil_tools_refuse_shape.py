#!/usr/bin/env python3
"""Hermetic: tools.json refuse list shape + no overlap with tool ids."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsRefuseShapeTest(unittest.TestCase):
    def test_refuse_shape(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        refuse = data.get("refuse")
        self.assertIsInstance(refuse, list)
        self.assertGreaterEqual(len(refuse), 5)
        self.assertEqual(len(refuse), len(set(refuse)), "duplicate refuse entry")
        for item in refuse:
            self.assertIsInstance(item, str)
            self.assertTrue(item.strip(), "empty refuse entry")
            self.assertEqual(item, item.strip())
        tool_ids = {t["id"] for t in data.get("tools") or []}
        overlap = set(refuse) & tool_ids
        self.assertFalse(overlap, f"refuse overlaps tool ids: {overlap}")


if __name__ == "__main__":
    unittest.main()
