#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['cloud-current.html', 'commands.html', 'commerce-agents-loop.html', 'commerce-agents.html', 'commercial.html', 'commons-flowchart.html', 'commons-slack-chunk.html', 'commons-slack.html', 'compress.html', 'cornell-craft-beverage-intake-lims.html', 'corrigan-specialty-fuel-blend-dossier-lims.html', 'court.html', 'csanalytical-expansion-crossline-lims.html', 'csplabs-express-capacity-assurance-lims.html', 'current-work.html', 'cweather.html', 'data-license.html', 'ddl-crosssite-method-proficiency-lims.html', 'delta.html', 'demand-survive.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909hTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
