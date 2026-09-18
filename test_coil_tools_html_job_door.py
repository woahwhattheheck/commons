#!/usr/bin/env python3
"""Hermetic: tools.html cites job.html door."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"


class CoilToolsHtmlJobDoorTest(unittest.TestCase):
    def test_job_door(self) -> None:
        text = TOOLS.read_text(encoding="utf-8")
        self.assertIn("job.html", text)
        self.assertIn("Job door", text)


if __name__ == "__main__":
    unittest.main()
