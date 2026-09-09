#!/usr/bin/env python3
"""Hermetic: wakeup.html cites TOOLS jobs door."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "wakeup.html"


class CoilWakeupToolsJobsTest(unittest.TestCase):
    def test_tools_jobs(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="tools-jobs"', text)
        self.assertIn("./job.html", text)
        self.assertIn("./tools.json", text)
        self.assertIn("./tools.html", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertNotIn('id="tools-board"', text)


if __name__ == "__main__":
    unittest.main()
