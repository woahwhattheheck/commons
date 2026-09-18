#!/usr/bin/env python3
"""Hermetic: commands.json /drop who is nonempty and cites issue/laptop."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsDropWhoTest(unittest.TestCase):
    def test_who(self) -> None:
        drop = next(c for c in json.loads(COMMANDS.read_text(encoding="utf-8"))["commands"] if c.get("id") == "drop")
        who = drop["who"]
        self.assertIsInstance(who, str)
        self.assertTrue(who.strip())
        low = who.lower()
        self.assertTrue("issue" in low or "laptop" in low or "anyone" in low)


if __name__ == "__main__":
    unittest.main()
