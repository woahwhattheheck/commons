#!/usr/bin/env python3
"""Hermetic: commands.json /computer-use commons cites titan_hands + offer."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsComputerUseCiteTest(unittest.TestCase):
    def test_computer_use(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        cmd = next(c for c in data["commands"] if c.get("id") == "computer-use")
        self.assertEqual(cmd["slash"], "/computer-use")
        commons = cmd["commons"]
        self.assertIn("titan_hands", commons)
        self.assertIn("offer.html", commons)


if __name__ == "__main__":
    unittest.main()
