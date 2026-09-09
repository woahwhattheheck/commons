#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json capabilities have unique nonempty ids."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessCapabilitiesIdsTest(unittest.TestCase):
    def test_ids(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        caps = json.loads(path.read_text(encoding="utf-8"))["capabilities"]
        self.assertIsInstance(caps, list)
        self.assertGreaterEqual(len(caps), 5)
        ids = []
        for c in caps:
            self.assertIsInstance(c, dict)
            i = c.get("id")
            self.assertIsInstance(i, str)
            self.assertTrue(i.strip())
            ids.append(i)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
