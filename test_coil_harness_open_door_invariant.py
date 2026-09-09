#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json open_door_invariant keeps no-auth law."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessOpenDoorInvariantTest(unittest.TestCase):
    def test_open_door(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        inv = json.loads(path.read_text(encoding="utf-8"))["open_door_invariant"]
        self.assertIsInstance(inv, str)
        self.assertTrue(inv.strip())
        low = inv.lower()
        self.assertIn("authorization", low)
        self.assertTrue("no auth" in low or "no auth," in low or "no auth " in low or "no auth" in inv.lower())
        self.assertIn("must not", low)


if __name__ == "__main__":
    unittest.main()
