#!/usr/bin/env python3
"""Hermetic: dests.html cites job.html for TOOLS jobs (Dest FROM FILE)."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "dests.html"


class CoilDestsJobHtmlTest(unittest.TestCase):
    def test_tools_jobs_note(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="tools-jobs"', text)
        self.assertIn("./job.html", text)
        self.assertIn("./tools.json", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("Dest FROM FILE", text)
        self.assertIn("337 NO", text)
        # not tools-board note remint class
        self.assertNotIn('id="tools-board"', text)


if __name__ == "__main__":
    unittest.main()
