#!/usr/bin/env python3
"""Hermetic: share.json open_per_claim map shape."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARE = ROOT / "share.json"


class CoilShareOpenPerClaimTest(unittest.TestCase):
    def test_open_per_claim(self) -> None:
        opc = json.loads(SHARE.read_text(encoding="utf-8"))["open_per_claim"]
        self.assertIsInstance(opc, dict)
        self.assertGreaterEqual(len(opc), 1)
        for key, val in opc.items():
            self.assertIsInstance(key, str)
            self.assertTrue(key.strip(), "empty open_per_claim key")
            self.assertIsInstance(val, int)
            self.assertGreaterEqual(val, 0)


if __name__ == "__main__":
    unittest.main()
