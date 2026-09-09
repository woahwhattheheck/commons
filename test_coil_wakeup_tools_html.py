#!/usr/bin/env python3
"""Hermetic: wakeup.html cites tools.html door."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wakeup.html"


class CoilWakeupToolsHtmlTest(unittest.TestCase):
    def test_tools(self) -> None:
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn("tools.html", text)


if __name__ == "__main__":
    unittest.main()
