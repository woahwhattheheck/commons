#!/usr/bin/env python3
"""Hermetic: harnesses/catalog.json updated is YYYY-MM-DD."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class CoilHarnessUpdatedTest(unittest.TestCase):
    def test_updated(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        updated = json.loads(path.read_text(encoding="utf-8"))["updated"]
        self.assertIsInstance(updated, str)
        self.assertRegex(updated, DATE_RE)


if __name__ == "__main__":
    unittest.main()
