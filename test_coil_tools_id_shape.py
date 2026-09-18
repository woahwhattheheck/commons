#!/usr/bin/env python3
"""Hermetic: tools.json tool ids are unique snake_case."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class CoilToolsIdShapeTest(unittest.TestCase):
    def test_ids(self) -> None:
        tools = json.loads(TOOLS.read_text(encoding="utf-8"))["tools"]
        ids = [t["id"] for t in tools]
        self.assertGreaterEqual(len(ids), 10)
        self.assertEqual(len(ids), len(set(ids)), "duplicate tool id")
        for tid in ids:
            self.assertTrue(ID_RE.match(tid), f"bad tool id shape: {tid}")


if __name__ == "__main__":
    unittest.main()
