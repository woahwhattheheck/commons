#!/usr/bin/env python3
"""Hermetic: tools.json job.fields exact ordered list."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
EXPECTED = ["from", "to", "id", "tool", "op"]


class CoilJobFieldsExactOrderTest(unittest.TestCase):
    def test_exact_order(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        fields = data["job"]["fields"]
        self.assertEqual(fields, EXPECTED)
        # no extras, no reorders
        self.assertEqual(len(fields), 5)
        self.assertEqual(fields[0], "from")
        self.assertEqual(fields[-1], "op")


if __name__ == "__main__":
    unittest.main()
