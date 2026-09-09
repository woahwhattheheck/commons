#!/usr/bin/env python3
"""Hermetic: wakeup.html keeps TOOLS jobs label."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wakeup.html"


class CoilWakeupToolsJobsLabelTest(unittest.TestCase):
    def test_label(self) -> None:
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn("TOOLS jobs", text)
        self.assertIn("invented tools", text)


if __name__ == "__main__":
    unittest.main()
