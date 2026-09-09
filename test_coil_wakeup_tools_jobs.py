#!/usr/bin/env python3
"""Hermetic: wakeup.html keeps #tools-jobs cite to job.html."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wakeup.html"


class CoilWakeupToolsJobsTest(unittest.TestCase):
    def test_tools_jobs(self) -> None:
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn('id="tools-jobs"', text)
        idx = text.index('id="tools-jobs"')
        window = text[idx : idx + 500]
        self.assertIn("job.html", window)


if __name__ == "__main__":
    unittest.main()
