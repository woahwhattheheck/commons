#!/usr/bin/env python3
"""Hermetic: commands.json law keeps board-door / harness / HTTP≠computer."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsLawTest(unittest.TestCase):
    def test_law(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        law = data["law"]
        self.assertIsInstance(law, str)
        self.assertTrue(law.strip())
        low = law.lower()
        self.assertIn("board", low)
        self.assertIn("harness", low)
        self.assertIn("http", low)
        self.assertIsInstance(data.get("commands"), list)
        self.assertGreater(len(data["commands"]), 0)
        # every command has id + slash
        for c in data["commands"]:
            self.assertIsInstance(c.get("id"), str)
            self.assertTrue(c["id"].strip())
            self.assertIsInstance(c.get("slash"), str)
            self.assertTrue(c["slash"].startswith("/"))


if __name__ == "__main__":
    unittest.main()
