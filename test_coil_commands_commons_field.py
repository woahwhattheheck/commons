#!/usr/bin/env python3
"""Hermetic: commands.json /tools commons cites board paths."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsCommonsFieldTest(unittest.TestCase):
    def test_tools_commons(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        tools = next(c for c in data["commands"] if c.get("id") == "tools")
        commons = tools["commons"]
        self.assertIsInstance(commons, str)
        self.assertIn("job.html", commons)
        self.assertIn("tools.json", commons)
        self.assertIn("tools.html", commons)
        self.assertIn("muhl-hook", commons)


if __name__ == "__main__":
    unittest.main()
