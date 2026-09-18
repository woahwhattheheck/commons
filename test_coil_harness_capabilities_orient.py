#!/usr/bin/env python3
"""Hermetic: harness capabilities include orient with discover tool."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessCapabilitiesOrientTest(unittest.TestCase):
    def test_orient(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        caps = json.loads(path.read_text(encoding="utf-8"))["capabilities"]
        orient = next((c for c in caps if c.get("id") == "orient"), None)
        self.assertIsNotNone(orient)
        tools = orient.get("public_mcp_tools") or []
        self.assertIn("discover_commons_capabilities", tools)
        self.assertIn("capabilities.html", orient.get("html") or [])


if __name__ == "__main__":
    unittest.main()
