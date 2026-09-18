#!/usr/bin/env python3
"""Hermetic: job.html cites PC button host/muhl_tools_once.py --go."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOB = ROOT / "job.html"


class CoilJobPcButtonTest(unittest.TestCase):
    def test_pc_button(self) -> None:
        text = JOB.read_text(encoding="utf-8")
        self.assertIn("PC button", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn('id="job-hook"', text)


if __name__ == "__main__":
    unittest.main()
