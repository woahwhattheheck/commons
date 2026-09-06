#!/usr/bin/env python3
"""Hermetic: webmcp.html points at live titanmcp pad."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "webmcp.html"
class LatchWebmcpTitanmcpPointerTest(unittest.TestCase):
    def test_pointer(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="titanmcp-pad-pointer"', text)
        self.assertIn("https://webmcp-pad.vercel.app/", text)
        self.assertIn("titanmcp 1.4.5", text)
if __name__ == "__main__":
    unittest.main()
