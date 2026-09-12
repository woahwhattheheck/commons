#!/usr/bin/env python3
"""Hermetic: commands.json every command has nonempty what + who."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsWhatNonemptyTest(unittest.TestCase):
    def test_what_who(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        for c in data["commands"]:
            self.assertIsInstance(c.get("what"), str)
            self.assertTrue(c["what"].strip(), f"empty what id={c.get('id')}")
            self.assertIsInstance(c.get("who"), str)
            self.assertTrue(c["who"].strip(), f"empty who id={c.get('id')}")


if __name__ == "__main__":
    unittest.main()
