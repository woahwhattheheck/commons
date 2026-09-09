#!/usr/bin/env python3
"""Hermetic: commands.json command id and slash values are unique."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsSlashUniqueTest(unittest.TestCase):
    def test_unique(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        cmds = data["commands"]
        ids = [c["id"] for c in cmds]
        slashes = [c["slash"] for c in cmds]
        self.assertEqual(len(ids), len(set(ids)), "duplicate command ids")
        self.assertEqual(len(slashes), len(set(slashes)), "duplicate slashes")
        for s in slashes:
            self.assertTrue(s.startswith("/"))
            self.assertGreater(len(s), 1)


if __name__ == "__main__":
    unittest.main()
