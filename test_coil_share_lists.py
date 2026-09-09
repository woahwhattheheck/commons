#!/usr/bin/env python3
"""Hermetic: share.json open/done/refused are job-row dict lists."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARE = ROOT / "share.json"
ROW_KEYS = ("id", "from", "ts", "status")


class CoilShareListsTest(unittest.TestCase):
    def test_lists(self) -> None:
        data = json.loads(SHARE.read_text(encoding="utf-8"))
        for key in ("open", "done", "refused"):
            arr = data[key]
            self.assertIsInstance(arr, list)
            for item in arr:
                self.assertIsInstance(item, dict)
                for rk in ROW_KEYS:
                    self.assertIn(rk, item)
                    self.assertIsInstance(item[rk], str)
                self.assertTrue(item["id"].strip())
        self.assertIsInstance(data["receipts"], int)
        self.assertGreaterEqual(data["receipts"], 0)


if __name__ == "__main__":
    unittest.main()
