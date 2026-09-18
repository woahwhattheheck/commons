#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json roads includes required road keys."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]
REQUIRED = {
    "commons-network-plugin",
    "gemini-sidecar",
    "git",
    "grok-cloud-plugin",
    "html-buttons",
    "public-mcp",
    "shared-equipment",
    "slack",
    "titan-hands-stdio",
    "tools-board",
}


class CoilHarnessRoadsKeysTest(unittest.TestCase):
    def test_roads(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        roads = json.loads(path.read_text(encoding="utf-8"))["roads"]
        self.assertIsInstance(roads, dict)
        missing = REQUIRED - set(roads)
        self.assertFalse(missing, f"missing roads: {sorted(missing)}")


if __name__ == "__main__":
    unittest.main()
