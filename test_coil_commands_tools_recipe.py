#!/usr/bin/env python3
"""Hermetic: commands.json /tools recipe cites job + PC button."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsToolsRecipeTest(unittest.TestCase):
    def test_tools_recipe(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        self.assertIsInstance(data.get("commands"), list)
        tools = next((c for c in data["commands"] if c.get("id") == "tools" or c.get("slash") == "/tools"), None)
        self.assertIsNotNone(tools, "/tools command missing")
        self.assertEqual(tools["slash"], "/tools")
        self.assertIsInstance(tools.get("do"), list)
        self.assertGreaterEqual(len(tools["do"]), 3)
        blob = " ".join(tools["do"]) + " " + str(tools.get("commons", ""))
        self.assertIn("job.html", blob)
        self.assertIn("muhl_tools_once.py --go", blob)
        self.assertIn("tools.json", blob)


if __name__ == "__main__":
    unittest.main()
