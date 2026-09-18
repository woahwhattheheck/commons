#!/usr/bin/env python3
"""Hermetic: tools.json super_mcp.door is wire.html."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsSuperMcpDoorTest(unittest.TestCase):
    def test_door(self) -> None:
        door = json.loads(TOOLS.read_text(encoding="utf-8"))["super_mcp"]["door"]
        self.assertEqual(door, "wire.html")


if __name__ == "__main__":
    unittest.main()
