#!/usr/bin/env python3
"""Hermetic: commands.json /pull-repo commons cites new-branch-and-pr skill."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsPullRepoCiteTest(unittest.TestCase):
    def test_pull_repo(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        cmd = next(c for c in data["commands"] if c.get("id") == "pull-repo")
        self.assertEqual(cmd["slash"], "/pull-repo")
        self.assertIn("new-branch-and-pr", cmd["commons"])


if __name__ == "__main__":
    unittest.main()
