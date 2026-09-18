#!/usr/bin/env python3
"""Hermetic: job.html keeps catalog job-hook id."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOB = ROOT / "job.html"


class CoilJobHookIdTest(unittest.TestCase):
    def test_hook(self) -> None:
        text = JOB.read_text(encoding="utf-8")
        self.assertIn('id="job-hook"', text)
        self.assertIn("tools.json", text)
        self.assertIn("Catalog job hook", text)


if __name__ == "__main__":
    unittest.main()
