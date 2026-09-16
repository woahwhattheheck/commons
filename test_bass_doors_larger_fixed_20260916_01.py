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

class BassLargerFixedBatchTest(unittest.TestCase):
    def test_exactly_twenty_doors(self) -> None:
        self.assertEqual(len(TARGETS), 20)
        for name in TARGETS:
            data = (ROOT / name).read_bytes()
            with self.subTest(name=name):
                self.assertIn(b"Larger fixed engagements", data)
                self.assertIn(b"diagnostic.html", data)
                self.assertNotIn(b"buy.stripe.com", data)

if __name__ == "__main__":
    unittest.main()
