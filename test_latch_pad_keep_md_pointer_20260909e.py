#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['ground/FINDER_ZERO.md', 'ground/FLAME.md', 'ground/FLEET.md', 'ground/FOREIGN_MAIN.md', 'ground/FOUNDRY_LAND_20260819.md', 'ground/FUTURE.md', 'ground/GEMMA_INGRESS.md', 'ground/GEMMA_TOKENIZER_MAP.md', 'ground/GITHUB_CALL_NOT_LOGIN.md', 'ground/GROK_APP_ROUTE.md', 'ground/GROK_AUTOMATION_HARVEST.md', 'ground/GROK_CLAUDE_HYGIENE.md', 'ground/GROK_HARNESS.md', 'ground/GROK_HYGIENE.md', 'ground/GROK_LAND_UPFRONT.md', 'ground/GROK_RECEIPT.md', 'ground/GROK_RECOVERY.md', 'ground/GROK_ROUTE.md', 'ground/GROK_SURFACES.md', 'ground/H002.md', 'ground/H009.md', 'ground/HARNESS.md', 'ground/HARNESS_ALREADY_LOGGED_IN.md', 'ground/HEAD.md', 'ground/HEAVY_LANES.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepMdPointer20260909eTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
