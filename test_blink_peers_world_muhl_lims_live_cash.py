#!/usr/bin/env python3
"""Hermetic peers/world/muhl/lims Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=["peers.html","the-world.html","muhl-train.html","corrigan-specialty-fuel-blend-dossier-lims.html","pcl-scope-sla-routing-lims.html","highpower-ssf-receiving-gate-lims.html","made-scientific-princeton-rapid-qc-lims.html","bsk-multilab-accession-parity-lims.html","torrent-workorder-commissioning-lims.html","sanair-asbestos-coc-router-lims.html"]
class T(unittest.TestCase):
    def test(self)->None:
        for name in FILES:
            text=(ROOT/name).read_text(encoding='utf-8')
            self.assertIn('id="live-cash"', text, name)
            self.assertIn('dealer-service-lead-rescue.html', text, name)
            self.assertNotIn('buy.stripe.com', text.split('id="live-cash"',1)[1][:900], name)
if __name__=='__main__':
    unittest.main()
