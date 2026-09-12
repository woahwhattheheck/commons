#!/usr/bin/env python3
"""Hermetic: every tools.json tool has a nonempty label."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsLabelNonemptyTest(unittest.TestCase):
    def test_labels(self) -> None:
        tools = json.loads(TOOLS.read_text(encoding="utf-8"))["tools"]
        self.assertGreaterEqual(len(tools), 10)
        labels = []
        for t in tools:
            label = t.get("label") or ""
            self.assertTrue(label.strip(), f"empty label on {t.get('id')}")
            labels.append(label.strip())
        self.assertEqual(len(labels), len(set(labels)), "duplicate tool labels")


if __name__ == "__main__":
    unittest.main()
