#!/usr/bin/env python3
"""Hermetic: titanmcp.html carries Pad KEEP live facts."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "titanmcp.html"
class LatchTitanmcpHtmlPadKeepFactsTest(unittest.TestCase):
    def test_facts(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        for n in ["1.4.5", "24 tools", "Agent Resources", "syncConsents", "get_setup_status", "https://webmcp-pad.vercel.app/"]:
            self.assertIn(n, text, f"missing {n}")
        self.assertNotIn("1.4.4", text)
if __name__ == "__main__":
    unittest.main()
