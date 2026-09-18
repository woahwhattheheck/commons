#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['health.html', 'highpower-ssf-receiving-gate-lims.html', 'hub-eyes.html', 'humans.html', 'image-drop.html', 'incoming-models.html', 'insights.html', 'interconnect.html', 'invoice-exception-pack.html', 'job.html', 'keep-sell.html', 'keyb.html', 'keys.html', 'kincell-rtp-qc-release-bridge-lims.html', 'land.html', 'landed-work.html', 'lda-receipt.html', 'ledger.html', 'lexington-mrf-diversion-gate.html', 'listing-registry.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909jTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
