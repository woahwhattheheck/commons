#!/usr/bin/env python3
"""Hermetic: manual.html keeps one-job / oldest-open law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualHtmlOneJobTest(unittest.TestCase):
    def test_one_job(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("One job", text)
        self.assertIn("Oldest open", text)


if __name__ == "__main__":
    unittest.main()
