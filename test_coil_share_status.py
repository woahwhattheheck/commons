#!/usr/bin/env python3
"""Hermetic: share.json open rows status OPEN; done/refused status nonempty."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARE = ROOT / "share.json"


class CoilShareStatusTest(unittest.TestCase):
    def test_status(self) -> None:
        data = json.loads(SHARE.read_text(encoding="utf-8"))
        for row in data["open"]:
            self.assertEqual(row["status"], "OPEN")
        for key in ("done", "refused"):
            for row in data[key]:
                self.assertIsInstance(row["status"], str)
                self.assertTrue(row["status"].strip())
                self.assertNotEqual(row["status"], "OPEN")


if __name__ == "__main__":
    unittest.main()
