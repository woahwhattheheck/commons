#!/usr/bin/env python3
"""Hermetic: harness capabilities include coordinate with observe_work."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessCapabilitiesCoordinateTest(unittest.TestCase):
    def test_coordinate(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        caps = json.loads(path.read_text(encoding="utf-8"))["capabilities"]
        cap = next((c for c in caps if c.get("id") == "coordinate"), None)
        self.assertIsNotNone(cap)
        tools = cap.get("public_mcp_tools") or []
        self.assertIn("observe_work", tools)
        self.assertIn("continue_from_observation", tools)
        html = cap.get("html") or []
        self.assertTrue(any("interconnect.html" in h or "agent-ops.html" in h for h in html))


if __name__ == "__main__":
    unittest.main()
