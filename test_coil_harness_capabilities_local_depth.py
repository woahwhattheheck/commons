#!/usr/bin/env python3
"""Hermetic: harness capabilities include local-depth with hands fallback."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessCapabilitiesLocalDepthTest(unittest.TestCase):
    def test_local_depth(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        caps = json.loads(path.read_text(encoding="utf-8"))["capabilities"]
        cap = next((c for c in caps if c.get("id") == "local-depth"), None)
        self.assertIsNotNone(cap)
        plugin = cap.get("plugin_tools") or []
        self.assertIn("local_checkout_status", plugin)
        local = cap.get("local_mcp_tools") or []
        self.assertIn("hands", local)
        fb = cap.get("fallback_public_mcp_tools") or []
        self.assertIn("fire_action", fb)


if __name__ == "__main__":
    unittest.main()
