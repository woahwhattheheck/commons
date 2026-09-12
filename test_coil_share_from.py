#!/usr/bin/env python3
"""Hermetic: share.json open/done/refused rows have nonempty from."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARE = ROOT / "share.json"


class CoilShareFromTest(unittest.TestCase):
    def test_from(self) -> None:
        data = json.loads(SHARE.read_text(encoding="utf-8"))
        for key in ("open", "done", "refused"):
            for row in data[key]:
                self.assertIsInstance(row.get("from"), str)
                self.assertTrue(row["from"].strip(), f"empty from in {key} id={row.get('id')}")


if __name__ == "__main__":
    unittest.main()
