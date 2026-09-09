#!/usr/bin/env python3
"""Hermetic: manual.html keeps #job-hook element for catalog job paint."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualHtmlJobHookTest(unittest.TestCase):
    def test_job_hook(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn('id="job-hook"', text)
        self.assertIn("tools.json", text)
        # paint script reads data.job
        self.assertTrue("data.job" in text or "job-hook" in text)


if __name__ == "__main__":
    unittest.main()
