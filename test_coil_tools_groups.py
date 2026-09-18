#!/usr/bin/env python3
"""Hermetic: tools.json tool groups are the known set; ops is a list."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
ALLOWED = {"INSTRUMENTS", "WHITEBOX", "WORLD"}


class CoilToolsGroupsTest(unittest.TestCase):
    def test_groups_and_ops_list(self) -> None:
        tools = json.loads(TOOLS.read_text(encoding="utf-8"))["tools"]
        self.assertGreaterEqual(len(tools), 10)
        seen = set()
        for t in tools:
            g = t.get("group")
            self.assertIn(g, ALLOWED, f"bad group {g} on {t.get('id')}")
            seen.add(g)
            ops = t.get("ops")
            self.assertIsInstance(ops, list, t.get("id"))
            # empty strings are allowed placeholders; nonempty ops must be unique
            solid = [o for o in ops if isinstance(o, str) and o.strip()]
            self.assertEqual(len(solid), len(set(solid)), f"duplicate ops on {t.get('id')}")
        self.assertEqual(seen, ALLOWED, "catalog missing a group")


if __name__ == "__main__":
    unittest.main()
