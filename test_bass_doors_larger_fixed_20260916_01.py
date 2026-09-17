#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGETS = (
    'builds.html',
    'feature-tracker.html',
    'flipbook.html',
    'glyphs.html',
    'gpt-grok-ship-loop.html',
    'grave-card.html',
    'grounding.html',
    'health.html',
    'image-drop.html',
    'incoming-models.html',
    'insights.html',
    'interconnect.html',
    'invoice-exception-pack.html',
    'keyb.html',
    'keys.html',
    'land.html',
    'landed-work.html',
    'lda-receipt.html',
    'lexington-mrf-diversion-gate.html',
    'listing-registry.html',
)

# Product door in this KEEP batch: verified livemode PL, not a pointer-only live-cash card.
VERIFIED_PRODUCT_CHECKOUT = {
    'invoice-exception-pack.html': b'https://buy.stripe.com/14A00i84Jdvz36hdxg43S0l',
}

class BassLargerFixedBatchTest(unittest.TestCase):
    def test_exactly_twenty_doors(self) -> None:
        self.assertEqual(len(TARGETS), 20)
        for name in TARGETS:
            data = (ROOT / name).read_bytes()
            with self.subTest(name=name):
                self.assertIn(b"Larger fixed engagements", data)
                self.assertIn(b"diagnostic.html", data)
                expected = VERIFIED_PRODUCT_CHECKOUT.get(name)
                if expected:
                    self.assertIn(expected, data)
                else:
                    self.assertNotIn(b"buy.stripe.com", data)

if __name__ == "__main__":
    unittest.main()
