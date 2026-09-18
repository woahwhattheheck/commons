#!/usr/bin/env python3
"""Hermetic: tools.json super_mcp.note keeps one-shared / no-remint law."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilSuperMcpNoteTest(unittest.TestCase):
    def test_super_mcp_note(self) -> None:
        note = (json.loads(TOOLS.read_text(encoding="utf-8"))["super_mcp"].get("note") or "").lower()
        self.assertTrue(note, "super_mcp.note missing")
        self.assertIn("do not remint", note)
        self.assertTrue("one shared" in note or "shared public mcp" in note, note)


if __name__ == "__main__":
    unittest.main()
