#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['docs/spark-mcp.md', 'docs/gemini-mcp.md', 'docs/mcp-carriers.md', 'llms.txt']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchDocsTitanmcpPointerTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text, f"{name} missing {n}")
if __name__ == "__main__":
    unittest.main()
