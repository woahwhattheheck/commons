#!/usr/bin/env python3
"""Hermetic: skills.html keeps #tools-jobs distinguishing skills vs TOOLS jobs."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS = ROOT / "skills.html"


class CoilSkillsToolsJobsTest(unittest.TestCase):
    def test_tools_jobs(self) -> None:
        text = SKILLS.read_text(encoding="utf-8")
        self.assertIn('id="tools-jobs"', text)
        idx = text.index('id="tools-jobs"')
        window = text[idx : idx + 600]
        self.assertIn("job.html", window)
        self.assertTrue("skill" in window.lower() or "TOOLS" in window)


if __name__ == "__main__":
    unittest.main()
