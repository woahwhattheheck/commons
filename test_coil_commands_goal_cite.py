#!/usr/bin/env python3
"""Hermetic: commands.json /goal commons cites MANUAL + commons-worker."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsGoalCiteTest(unittest.TestCase):
    def test_goal(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        goal = next(c for c in data["commands"] if c.get("id") == "goal")
        self.assertEqual(goal["slash"], "/goal")
        commons = goal["commons"]
        self.assertIn("MANUAL.md", commons)
        self.assertIn("commons-worker", commons)


if __name__ == "__main__":
    unittest.main()
