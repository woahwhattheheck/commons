#!/usr/bin/env python3
"""Hermetic: capabilities.html paints tools_road + roads.tools-board (≠ job-hook remint)."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "capabilities.html"


class CoilCapabilitiesToolsRoadPaintTest(unittest.TestCase):
    def test_tools_road_paint(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("row.tools_road", text)
        self.assertIn('id="roads"', text)
        self.assertIn("catalog.roads", text)
        self.assertIn("tools-board", text)
        self.assertIn('href="./tools.html"', text)
        # not a job/super_mcp paint remint
        self.assertNotIn("data.job", text)
        self.assertNotIn("super_mcp", text)


if __name__ == "__main__":
    unittest.main()
