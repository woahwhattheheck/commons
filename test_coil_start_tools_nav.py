#!/usr/bin/env python3
"""Hermetic: start.html cites tools door."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START = ROOT / "start.html"


class CoilStartToolsNavTest(unittest.TestCase):
    def test_nav(self) -> None:
        text = START.read_text(encoding="utf-8")
        self.assertIn("tools.html", text)


if __name__ == "__main__":
    unittest.main()
