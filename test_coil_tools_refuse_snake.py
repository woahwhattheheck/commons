#!/usr/bin/env python3
"""Hermetic: tools.json refuse[] entries are unique snake_case ids."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


class CoilToolsRefuseSnakeTest(unittest.TestCase):
    def test_refuse_snake(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        refuse = data["refuse"]
        self.assertIsInstance(refuse, list)
        self.assertGreater(len(refuse), 0)
        self.assertEqual(len(refuse), len(set(refuse)))
        for item in refuse:
            self.assertIsInstance(item, str)
            self.assertRegex(item, SNAKE)


if __name__ == "__main__":
    unittest.main()
