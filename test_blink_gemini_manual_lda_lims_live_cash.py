#!/usr/bin/env python3
"""Hermetic gemini/manual/lda/lims Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=["gemini-mcp.html","manual.html","lda-receipt.html","mirror-capsule.html","ptl-controlled-sample-order-preflight.html","billings-bid-1421-acceptance-runner.html","kincell-rtp-qc-release-bridge-lims.html","wadsworth-five-site-consolidation-lims.html","ward-feed-nirs-intake-validator-lims.html","canyon-multisite-regulated-intake.html"]
class T(unittest.TestCase):
    def test(self)->None:
        for name in FILES:
            text=(ROOT/name).read_text(encoding='utf-8')
            self.assertIn('id="live-cash"', text, name)
            self.assertIn('dealer-service-lead-rescue.html', text, name)
if __name__=='__main__':
    unittest.main()
