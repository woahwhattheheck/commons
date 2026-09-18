#!/usr/bin/env python3
"""Hermetic: dests.html keeps #tools-jobs cite to job.html."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DESTS = ROOT / "dests.html"


class CoilDestsToolsJobsTest(unittest.TestCase):
    def test_tools_jobs(self) -> None:
        text = DESTS.read_text(encoding="utf-8")
        self.assertIn('id="tools-jobs"', text)
        # window around the id must cite job
        idx = text.index('id="tools-jobs"')
        window = text[idx : idx + 500]
        self.assertIn("job.html", window)
        self.assertTrue("TOOLS" in window or "tools" in window.lower())


if __name__ == "__main__":
    unittest.main()
