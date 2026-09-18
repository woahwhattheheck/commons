#!/usr/bin/env python3
"""Hermetic: job.html keeps No JavaScript law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOB = ROOT / "job.html"


class CoilJobNoJavascriptTest(unittest.TestCase):
    def test_no_js(self) -> None:
        text = JOB.read_text(encoding="utf-8")
        self.assertIn("No JavaScript", text)


if __name__ == "__main__":
    unittest.main()
