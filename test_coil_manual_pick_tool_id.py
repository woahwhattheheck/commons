#!/usr/bin/env python3
"""Hermetic: manual.html Pick a tool id from the catalog."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualPickToolIdTest(unittest.TestCase):
    def test_pick_tool_id(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Pick a tool id from the catalog", text)


if __name__ == "__main__":
    unittest.main()
