#!/usr/bin/env python3
"""Hermetic: job.html keeps #job-hook citing tools.json job."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOB = ROOT / "job.html"


class CoilJobHtmlJobHookTest(unittest.TestCase):
    def test_job_hook(self) -> None:
        text = JOB.read_text(encoding="utf-8")
        self.assertIn('id="job-hook"', text)
        idx = text.index('id="job-hook"')
        window = text[idx : idx + 500]
        self.assertIn("tools.json", window)
        self.assertIn("muhl_tools_once.py --go", window)
        self.assertIn("to: TOOLS", window)


if __name__ == "__main__":
    unittest.main()
