#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json shared has required keys."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]
REQUIRED = {
    "remote_mcp",
    "authentication",
    "protocol",
    "action_pad",
    "truth",
    "carrier_boundary",
}


class CoilHarnessSharedKeysTest(unittest.TestCase):
    def test_shared(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        shared = json.loads(path.read_text(encoding="utf-8"))["shared"]
        self.assertIsInstance(shared, dict)
        missing = REQUIRED - set(shared)
        self.assertFalse(missing, f"missing shared keys: {sorted(missing)}")
        for k in REQUIRED:
            self.assertTrue(str(shared[k]).strip(), f"empty shared.{k}")


if __name__ == "__main__":
    unittest.main()
