#!/usr/bin/env python3
"""Hermetic: tools.html keeps one-job / oldest-open law."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"


class CoilToolsHtmlOneJobTest(unittest.TestCase):
    def test_one_job(self) -> None:
        text = TOOLS.read_text(encoding="utf-8")
        self.assertIn("One job per PC", text)
        self.assertIn("Oldest open job", text)


if __name__ == "__main__":
    unittest.main()
