#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['docs/TITAN_HANDS_PEERS.md', 'mcp-tool-drift.html', 'mcp-conformance.html', 'commons_mcp_app.html', 'pixel.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatchTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text, f"{name} missing {n}")
if __name__ == "__main__":
    unittest.main()
