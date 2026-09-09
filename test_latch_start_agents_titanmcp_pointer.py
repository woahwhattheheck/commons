#!/usr/bin/env python3
"""Hermetic: START.md + AGENTS.md point at live titanmcp pad."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ["START.md", "AGENTS.md"]
REQUIRED = ["https://webmcp-pad.vercel.app/", "titanmcp 1.4.5", "24 tools", "./titanmcp.html", "./webmcp.html"]
class LatchStartAgentsTitanmcpPointerTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text, f"{name} missing {n}")
if __name__ == "__main__":
    unittest.main()
