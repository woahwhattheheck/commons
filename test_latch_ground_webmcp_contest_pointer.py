#!/usr/bin/env python3
"""Hermetic: ground/WEBMCP.md names contest titanmcp 1.4.5."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "ground" / "WEBMCP.md"
class LatchGroundWebmcpContestPointerTest(unittest.TestCase):
    def test_contest_pointer(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn("https://webmcp-pad.vercel.app/", text)
        self.assertIn("titanmcp 1.4.5", text)
        self.assertIn("24 tools", text)
        self.assertIn("../titanmcp.html", text)
        self.assertIn("## Live cash", text)
if __name__ == "__main__":
    unittest.main()
