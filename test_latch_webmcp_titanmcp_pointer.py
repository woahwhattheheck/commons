#!/usr/bin/env python3
"""Hermetic: webmcp.html Live cash + live titanmcp pad pointer."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "webmcp.html"
class LatchWebmcpTitanmcpPointerTest(unittest.TestCase):
    def test_pointer_and_cash(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="titanmcp-pad-pointer"', text)
        self.assertIn("https://webmcp-pad.vercel.app/", text)
        self.assertIn("1.4.5", text)
        self.assertIn('id="live-cash"', text)
        self.assertIn("./agent-rescue.html", text)
        self.assertIn("$29 Autopsy", text)
        self.assertNotIn("buy.stripe.com", text)
if __name__ == "__main__":
    unittest.main()
