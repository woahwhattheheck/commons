#!/usr/bin/env python3
"""Hermetic: commands.json /tools slash recipe enriched (≠ tools-board HTML notes)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

DOC = Path(__file__).resolve().parent / "commands.json"


class CoilCommandsJsonToolsEnrichTest(unittest.TestCase):
    def test_tools_command(self) -> None:
        data = json.loads(DOC.read_text(encoding="utf-8"))
        tools = next(c for c in data["commands"] if c.get("id") == "tools")
        self.assertEqual(tools.get("slash"), "/tools")
        blob = json.dumps(tools)
        self.assertIn("job.html", blob)
        self.assertIn("manual.html", blob)
        self.assertIn("tools.json", blob)
        self.assertIn("muhl_tools_once.py --go", blob)
        self.assertIn("tools-board", blob)
        self.assertIn("Not an Action Pad verb", tools.get("what") or "")


if __name__ == "__main__":
    unittest.main()
