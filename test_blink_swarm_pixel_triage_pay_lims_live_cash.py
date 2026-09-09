#!/usr/bin/env python3
"""Hermetic swarm/pixel/triage/pay/lims Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HTML=["swarm-dc.html","slack-tags.html","pixel-portfolio.html","agent-triage.html","ddl-crosssite-method-proficiency-lims.html","chemtechford-short-hold-intake-lims.html","weck-coc-preaccession-validator-lims.html","westpak-scope-capacity-routing-lims.html","agriseed-rush-work-allocator-lims.html"]
MD=["ground/PIXEL_HEARTBEAT.md","ground/PAY.md","ground/PAYMENT_CAPABILITY.md"]
class T(unittest.TestCase):
    def test(self)->None:
        for name in HTML:
            text=(ROOT/name).read_text(encoding='utf-8')
            self.assertIn('id="live-cash"', text, name)
            self.assertIn('dealer-service-lead-rescue.html', text, name)
        for name in MD:
            text=(ROOT/name).read_text(encoding='utf-8')
            self.assertIn('## Live cash', text, name)
            self.assertIn('dealer-service-lead-rescue.html', text, name)
if __name__=='__main__':
    unittest.main()
