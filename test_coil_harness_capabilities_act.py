#!/usr/bin/env python3
"""Hermetic: harness capabilities include act with fire_action."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessCapabilitiesActTest(unittest.TestCase):
    def test_act(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        caps = json.loads(path.read_text(encoding="utf-8"))["capabilities"]
        act = next((c for c in caps if c.get("id") == "act"), None)
        self.assertIsNotNone(act)
        tools = act.get("public_mcp_tools") or []
        self.assertIn("fire_action", tools)
        self.assertIn("action.html", act.get("html") or [])


if __name__ == "__main__":
    unittest.main()
