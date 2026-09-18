#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json tools-board road (≠ job-hook remint)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

CAT = Path(__file__).resolve().parent / "harnesses" / "catalog.json"


class CoilHarnessToolsBoardRoadTest(unittest.TestCase):
    def test_tools_board_road(self) -> None:
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        road = (cat.get("roads") or {}).get("tools-board")
        self.assertIsInstance(road, dict)
        self.assertIn("tools.html", road.get("connect") or "")
        self.assertIn("muhl_tools_once.py --go", road.get("connect") or "")
        self.assertIn("job.html", road.get("connect") or "")
        grokbot = next(h for h in cat["harnesses"] if h.get("id") == "grokbot")
        self.assertEqual(grokbot.get("tools_road"), "tools-board")
        self.assertIn("Coil door: TOOLS", grokbot.get("note") or "")


if __name__ == "__main__":
    unittest.main()
