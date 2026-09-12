#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json keeps tools-board road + PC button cite."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [
    ROOT / "harnesses" / "catalog.json",
    ROOT / "catalog.json",
]


class CoilHarnessToolsBoardTest(unittest.TestCase):
    def test_tools_board_road(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        roads = data["roads"]
        self.assertIn("tools-board", roads)
        road = roads["tools-board"]
        blob = json.dumps(road)
        self.assertIn("muhl_tools_once.py --go", blob)
        self.assertIn("job.html", blob)
        self.assertIn("tools.html", blob)


if __name__ == "__main__":
    unittest.main()
