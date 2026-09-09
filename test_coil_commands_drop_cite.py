#!/usr/bin/env python3
"""Hermetic: commands.json /drop cites DROP.md + muhl-hook token."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsDropCiteTest(unittest.TestCase):
    def test_drop(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        drop = next((c for c in data["commands"] if c.get("id") == "drop" or c.get("slash") == "/drop"), None)
        self.assertIsNotNone(drop)
        blob = json.dumps(drop)
        self.assertIn("DROP.md", blob)
        self.assertIn("muhl-hook", blob)
        self.assertEqual(drop["slash"], "/drop")


if __name__ == "__main__":
    unittest.main()
