#!/usr/bin/env python3
"""Hermetic pack/subzero/proof/salesforce Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=["pack-is-ready-to-run.html","pack-quality-tier.html","what-a-pack-is.html","demand-survive.html","subzero-quote.html","subzero-receipt.html","subzero-proof.html","proof-spiral-succinct-argument.html","salesforce-contact-preflight.html"]
class T(unittest.TestCase):
    def test(self)->None:
        for name in FILES:
            text=(ROOT/name).read_text(encoding='utf-8')
            self.assertIn('id="live-cash"', text, name)
            self.assertIn('dealer-service-lead-rescue.html', text, name)
if __name__=='__main__':
    unittest.main()
