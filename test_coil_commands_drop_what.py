#!/usr/bin/env python3
"""Hermetic: commands.json /drop what cites size gate."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsDropWhatTest(unittest.TestCase):
    def test_what(self) -> None:
        drop = next(c for c in json.loads(COMMANDS.read_text(encoding="utf-8"))["commands"] if c.get("id") == "drop")
        what = drop["what"]
        self.assertIsInstance(what, str)
        self.assertIn("size", what.lower())
        self.assertIn("gate", what.lower())


if __name__ == "__main__":
    unittest.main()
