#!/usr/bin/env python3
"""Hermetic: tools.json job.note cites share/button and no-remint."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilJobNoteTest(unittest.TestCase):
    def test_job_note(self) -> None:
        note = (json.loads(TOOLS.read_text(encoding="utf-8"))["job"].get("note") or "").lower()
        self.assertTrue(note, "job.note missing")
        self.assertIn("do not remint", note)
        self.assertTrue("muhl_tools_once" in note or "share/button" in note or "share" in note, note)
        self.assertIn("job", note)


if __name__ == "__main__":
    unittest.main()
