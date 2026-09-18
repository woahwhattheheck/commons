#!/usr/bin/env python3
"""Hermetic: wakeup.html keeps titanmcp contest pad pointer."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wakeup.html"


class CoilWakeupTitanmcpPadTest(unittest.TestCase):
    def test_pad(self) -> None:
        text = WAKE.read_text(encoding="utf-8")
        self.assertIn('id="titanmcp-pad-pointer"', text)
        self.assertIn("webmcp-pad.vercel.app", text)
        self.assertIn("titanmcp", text.lower())


if __name__ == "__main__":
    unittest.main()
