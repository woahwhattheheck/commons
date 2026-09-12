#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['apl-fda-polymer-compliance-dossier-lims.html', 'authorship.html', 'baddl-eia-accession-release-lims.html', 'bazaar.html', 'billings-bid-1421-acceptance-runner.html', 'billings-bid-1421-operations-runner.html', 'billings-bid-1421-partner-recon.html', 'board.html', 'bsk-multilab-accession-parity-lims.html', 'builds.html', 'business-packs.html', 'canyon-multisite-regulated-intake.html', 'capabilities.html', 'catalog.html', 'catering-deposit-rescue.html', 'ccc-snapshot-toolchain.html', 'chemtechford-short-hold-intake-lims.html', 'clans.html', 'clark-d4172-proficiency-lims.html', 'claude-paste.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909gTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
