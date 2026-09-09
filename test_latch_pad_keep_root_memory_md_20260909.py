#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['GRANTS.md', 'harness-ping-get.md', 'window-miss.md', 'GEMINI.md', 'fresh.md', 'leftover-census.md', 'play-inhabit.md', 'DROP.md', 'CRAWLERS.md', 'DIRECTIVES.md', 'change.md', 'CLAUDE.md', 'ENTRY.md', 'peers.md', 'WRITING.md', 'mirror-writeback.md', 'owner-context.md', 'ship-loop-prompt.md', 'occupancy.md', 'PANEL.md', 'KEYB.md', 'ISSUE.md', 'health-canary.md', 'memory/README.md', 'memory/GROK_APP_ROUTE.md', 'memory/HOLD_QUOTE.md', 'memory/READ_IS_VOLTAGE.md', 'memory/GROK_LAND_UPFRONT.md', 'memory/CODEX_BUILDER.md', 'memory/CURSOR_HALT.md', 'memory/CLAUDE_OWNER_WORDS.md', 'memory/LAW.md', 'by/DEMON/REDTEAM.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class T(unittest.TestCase):
    def test_all(self):
        for name in PAGES:
            with self.subTest(page=name):
                text=(ROOT/name).read_text(encoding='utf-8')
                for n in REQUIRED: self.assertIn(n, text)
if __name__ == '__main__':
    unittest.main()
