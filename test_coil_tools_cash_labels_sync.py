#!/usr/bin/env python3
"""Hermetic: tools.json cash.doors labels appear in tools-cash.html."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
SHELF = ROOT / "tools-cash.html"


class CoilToolsCashLabelsSyncTest(unittest.TestCase):
    def test_labels_on_shelf(self) -> None:
        doors = json.loads(TOOLS.read_text(encoding="utf-8"))["cash"]["doors"]
        shelf = SHELF.read_text(encoding="utf-8")
        self.assertGreaterEqual(len(doors), 5)
        labels = [d["label"] for d in doors]
        self.assertEqual(len(labels), len(set(labels)), "duplicate cash door label")
        for label in labels:
            self.assertIn(label, shelf, f"label missing from tools-cash.html: {label}")


if __name__ == "__main__":
    unittest.main()
