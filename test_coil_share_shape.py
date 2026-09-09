#!/usr/bin/env python3
"""Hermetic: share.json top-level shape stays locked."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARE = ROOT / "share.json"
REQUIRED = ("law", "open", "done", "refused", "open_per_claim", "receipts", "button")


class CoilShareShapeTest(unittest.TestCase):
    def test_share_shape(self) -> None:
        data = json.loads(SHARE.read_text(encoding="utf-8"))
        for key in REQUIRED:
            self.assertIn(key, data, f"missing share.json key {key}")
        self.assertIsInstance(data["law"], str)
        self.assertIsInstance(data["open"], list)
        self.assertIsInstance(data["done"], list)
        self.assertIsInstance(data["refused"], list)
        self.assertIsInstance(data["open_per_claim"], dict)
        self.assertIsInstance(data["receipts"], int)
        self.assertIsInstance(data["button"], str)
        self.assertGreaterEqual(data["receipts"], 0)


if __name__ == "__main__":
    unittest.main()
