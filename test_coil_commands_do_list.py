#!/usr/bin/env python3
"""Hermetic: commands.json every command has nonempty do[] list."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsDoListTest(unittest.TestCase):
    def test_do_list(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        for c in data["commands"]:
            do = c.get("do")
            self.assertIsInstance(do, list, f"do not list id={c.get('id')}")
            self.assertGreaterEqual(len(do), 1, f"empty do id={c.get('id')}")
            for step in do:
                self.assertIsInstance(step, str)
                self.assertTrue(step.strip())


if __name__ == "__main__":
    unittest.main()
