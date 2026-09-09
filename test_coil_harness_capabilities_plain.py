#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json every capability has nonempty plain."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessCapabilitiesPlainTest(unittest.TestCase):
    def test_plain(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        caps = json.loads(path.read_text(encoding="utf-8"))["capabilities"]
        plains = []
        for c in caps:
            plain = c.get("plain")
            self.assertIsInstance(plain, str)
            self.assertTrue(plain.strip(), f"empty plain id={c.get('id')}")
            plains.append(plain.strip())
        self.assertEqual(len(plains), len(set(plains)), "duplicate plain strings")


if __name__ == "__main__":
    unittest.main()
