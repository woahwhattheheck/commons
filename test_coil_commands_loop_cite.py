#!/usr/bin/env python3
"""Hermetic: commands.json /loop commons cites wake.html + ping-wake."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsLoopCiteTest(unittest.TestCase):
    def test_loop(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        loop = next(c for c in data["commands"] if c.get("id") == "loop")
        self.assertEqual(loop["slash"], "/loop")
        self.assertIn("wake.html", loop["commons"])
        self.assertIn("ping-wake", loop["commons"])


if __name__ == "__main__":
    unittest.main()
