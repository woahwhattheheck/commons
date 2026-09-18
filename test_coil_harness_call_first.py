#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json call_first discover roads."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]
REQUIRED = ("tool", "resource", "http", "static", "buttons")


class CoilHarnessCallFirstTest(unittest.TestCase):
    def test_call_first(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        cf = json.loads(path.read_text(encoding="utf-8"))["call_first"]
        self.assertIsInstance(cf, dict)
        for k in REQUIRED:
            self.assertIn(k, cf)
            self.assertIsInstance(cf[k], str)
            self.assertTrue(cf[k].strip())
        self.assertEqual(cf["tool"], "discover_commons_capabilities")
        self.assertTrue(cf["resource"].startswith("commons://"))
        self.assertTrue(cf["http"].startswith("https://"))
        self.assertTrue(cf["static"].endswith("harnesses/catalog.json"))
        self.assertIn("capabilities.html", cf["buttons"])


if __name__ == "__main__":
    unittest.main()
