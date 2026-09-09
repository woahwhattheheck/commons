#!/usr/bin/env python3
"""Hermetic aquatrace + commerce ground Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HTML=["aquatrace-work-order-c-reporting-offline.html","aquatrace-work-order-b-production-foundation.html","aquatrace-work-order-f-release-readiness.html","aquatrace-ops-acceptance.html","at-grok-cmdp-evidence.html","at-grok-adapter-evidence.html"]
MD=["ground/COMMERCE.md","ground/STRIPE.md","ground/PAYMENT_READY.md","ground/HUMAN_OUTCOMES.md","ground/SCOPE_TO_DELIVERY.md"]
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
