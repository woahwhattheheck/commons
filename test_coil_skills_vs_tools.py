#!/usr/bin/env python3
"""Hermetic: skills.html distinguishes worker skills from TOOLS jobs."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "skills.html"


class CoilSkillsVsToolsTest(unittest.TestCase):
    def test_not_tools_job(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="tools-jobs"', text)
        self.assertIn("Not a TOOLS job", text)
        self.assertIn("./job.html", text)
        self.assertIn("./tools.json", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)


if __name__ == "__main__":
    unittest.main()
