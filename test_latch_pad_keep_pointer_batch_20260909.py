#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['host/titan_hands/GROK_HANDOFF.md', 'host/titan_hands/ARCHITECTURE.md', 'ground/MCP_WAKE_JOB.md', 'ground/SLACK_SPARK_MCP_DRIVER.md', 'gemini-mcp.html', 'reach.html', 'wakeup.html', 'action.html', 'by/LATCH.html', 'independent_commons_mcp/console.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909Test(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text, f"{name} missing {n}")
if __name__ == "__main__":
    unittest.main()
