#!/usr/bin/env python3
"""Hermetic: MANUAL + job.html cite tools.json job hook (≠ Live-cash)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "ground" / "MANUAL.md"
JOB = ROOT / "job.html"


class CoilManualJobCiteTest(unittest.TestCase):
    def test_manual_cites_job_object(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        section = text.split("## File a job", 1)[1].split("## Catalog", 1)[0]
        self.assertIn("Catalog job hook", section)
        self.assertIn("../tools.json", section)
        self.assertIn("`job`", section)
        self.assertIn("coil-tools-json-job-hook-20260905-01", section)

    def test_job_html_static_hook(self) -> None:
        text = JOB.read_text(encoding="utf-8")
        self.assertIn('id="job-hook"', text)
        self.assertIn("./tools.json", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("to: TOOLS", text)
        # still no JS fetch (page law)
        self.assertNotIn("fetch(", text)


if __name__ == "__main__":
    unittest.main()
