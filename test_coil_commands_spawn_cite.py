#!/usr/bin/env python3
"""Hermetic: commands.json /spawn commons cites commands.html#spawn."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsSpawnCiteTest(unittest.TestCase):
    def test_spawn(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        spawn = next(c for c in data["commands"] if c.get("id") == "spawn")
        self.assertEqual(spawn["slash"], "/spawn")
        self.assertIn("commands.html#spawn", spawn["commons"])
        self.assertIn("commons-worker", spawn["commons"])


if __name__ == "__main__":
    unittest.main()
