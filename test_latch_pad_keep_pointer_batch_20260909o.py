#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['task-forge.html', 'telegram.html', 'the-world.html', 'tips.html', 'titan-hands.html', 'toolbench.html', 'tools-cash.html', 'tools.html', 'topics.html', 'torrent-workorder-commissioning-lims.html', 'trace-sila-ml-iatf-lims.html', 'trust.html', 'unbuilt-items.html', 'wadsworth-five-site-consolidation-lims.html', 'wake.html', 'ward-feed-nirs-intake-validator-lims.html', 'weather.html', 'website-people-email-book.html', 'weck-coc-preaccession-validator-lims.html', 'westpak-scope-capacity-routing-lims.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909oTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
