#!/usr/bin/env python3
"""Hermetic: share.json open/done/refused row ids are unique within and across lists."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARE = ROOT / "share.json"


class CoilShareOpenIdsTest(unittest.TestCase):
    def test_unique_ids(self) -> None:
        data = json.loads(SHARE.read_text(encoding="utf-8"))
        seen: set[str] = set()
        for key in ("open", "done", "refused"):
            ids = [row["id"] for row in data[key]]
            self.assertEqual(len(ids), len(set(ids)), f"dupes inside {key}")
            for i in ids:
                self.assertNotIn(i, seen, f"id {i} repeats across lists")
                seen.add(i)


if __name__ == "__main__":
    unittest.main()
