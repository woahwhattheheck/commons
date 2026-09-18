#!/usr/bin/env python3
"""Hermetic: job.html keeps No JavaScript law + GitHub issue form."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOB = ROOT / "job.html"


class CoilJobHtmlNoJsTest(unittest.TestCase):
    def test_no_js(self) -> None:
        text = JOB.read_text(encoding="utf-8")
        self.assertIn("No JavaScript", text)
        self.assertIn("<form", text)
        self.assertIn("github.com/woahwhattheheck/commons/issues/new", text)
        self.assertIsNone(re.search(r"<script\b", text, re.I))


if __name__ == "__main__":
    unittest.main()
