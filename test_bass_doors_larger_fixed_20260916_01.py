#!/usr/bin/env python3
from __future__ import annotations
import re
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

# Product doors in this KEEP batch: verified livemode PLs, not pointer-only
# live-cash cards. land.html convert shelf reuses existing Autopsy $29 +
# White Box hour $250 Payment Links (wire-entry-land-convert-shelf-20260917-01).
VERIFIED_PRODUCT_CHECKOUT = {
    'invoice-exception-pack.html': (
        b'https://buy.stripe.com/14A00i84Jdvz36hdxg43S0l',
    ),
    'land.html': (
        b'https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g',
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
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
                    for url in expected:
                        self.assertIn(url, data)
                    found = {
                        b'https://buy.stripe.com/' + path
                        for path in re.findall(
                            br'https?://buy\.stripe\.com/([A-Za-z0-9_-]+)',
                            data,
                        )
                    }
                    self.assertEqual(found, set(expected))
                else:
                    self.assertNotIn(b"buy.stripe.com", data)

if __name__ == "__main__":
    unittest.main()
