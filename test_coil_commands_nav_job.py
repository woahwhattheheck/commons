#!/usr/bin/env python3
"""Hermetic: commands.html nav cites job.html."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "commands.html"


class CoilCommandsNavJobTest(unittest.TestCase):
    def test_nav_job(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('./job.html', text)
        self.assertIn('./tools.html', text)
        self.assertNotIn('id="tools-board"', text)


if __name__ == "__main__":
    unittest.main()
