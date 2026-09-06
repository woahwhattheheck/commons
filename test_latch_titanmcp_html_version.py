#!/usr/bin/env python3
"""Hermetic: commons titanmcp.html matches live 1.4.5."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "titanmcp.html"
class LatchTitanmcpHtmlVersionTest(unittest.TestCase):
    def test_version_145(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("1.4.5", text)
        self.assertNotIn("1.4.4", text)
        self.assertIn("https://webmcp-pad.vercel.app/", text)
        self.assertIn('id="live-cash"', text)
if __name__ == "__main__":
    unittest.main()
