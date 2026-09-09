#!/usr/bin/env python3
"""Hermetic: job.html cites tools.json + manual.html."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOB = ROOT / "job.html"


class CoilJobToolsJsonCiteTest(unittest.TestCase):
    def test_cites(self) -> None:
        text = JOB.read_text(encoding="utf-8")
        self.assertIn("tools.json", text)
        self.assertIn("manual.html", text)


if __name__ == "__main__":
    unittest.main()
