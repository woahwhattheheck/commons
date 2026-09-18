#!/usr/bin/env python3
"""Hermetic: wakeup.html cites PC command host/muhl_tools_once.py --go."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wakeup.html"


class CoilWakeupMuhlOnceTest(unittest.TestCase):
    def test_muhl(self) -> None:
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("host/muhl_tools_once.py", text)


if __name__ == "__main__":
    unittest.main()
