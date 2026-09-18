#!/usr/bin/env python3
"""Hermetic: job.html keeps File job submit button."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOB = ROOT / "job.html"


class CoilJobFileJobButtonTest(unittest.TestCase):
    def test_button(self) -> None:
        text = JOB.read_text(encoding="utf-8")
        self.assertIn("File job", text)
        self.assertIn("<button", text)


if __name__ == "__main__":
    unittest.main()
