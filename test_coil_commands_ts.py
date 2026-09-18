#!/usr/bin/env python3
"""Hermetic: commands.json ts is ISO-8601 UTC."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class CoilCommandsTsTest(unittest.TestCase):
    def test_ts(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        ts = data["ts"]
        self.assertIsInstance(ts, str)
        self.assertRegex(ts, TS_RE)


if __name__ == "__main__":
    unittest.main()
