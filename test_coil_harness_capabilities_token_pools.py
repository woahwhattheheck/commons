#!/usr/bin/env python3
"""Hermetic: harness capabilities include token-pools on shared-equipment."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessCapabilitiesTokenPoolsTest(unittest.TestCase):
    def test_token_pools(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        caps = json.loads(path.read_text(encoding="utf-8"))["capabilities"]
        cap = next((c for c in caps if c.get("id") == "token-pools"), None)
        self.assertIsNotNone(cap)
        self.assertEqual(cap.get("preferred_road"), "shared-equipment")
        equip = cap.get("equipment_tools") or []
        self.assertIn("token_pool_status", equip)


if __name__ == "__main__":
    unittest.main()
