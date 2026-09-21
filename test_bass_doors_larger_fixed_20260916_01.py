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
# live-cash cards. land.html convert shelf reuses existing # White Box hour $250 Payment Links (wire-entry-land-convert-shelf-20260917-01).
# keyb.html convert shelf reuses the same two live Payment Links
# (latch-head-keyb-convert-shelf-20260917-01). builds.html and keys.html
# already carry those same two live Payment Links on current main.
# health.html convert shelf copies the nine live Payment Links from
# payment-capability.html (type-patent-health-convert-shelf-20260917-01).
# glyphs.html convert shelf reuses the same two live Payment Links
# (type-embassy-glyphs-convert-shelf-20260917-01).
# flipbook.html convert shelf reuses the same two live Payment Links
# (type-flipbook-compress-convert-shelf-20260917-01).
# insights.html and grounding.html convert shelves reuse the same two
# live Payment Links (type-insights-grounding-convert-shelf-20260917-01).
# interconnect.html convert shelf reuses the White Box hour link
# (anvil-opendoor-interconnect-convert-shelf-20260917-01).
# landed-work.html convert shelf reuses the White Box hour link
# (sledge-mergeonpr-landedwork-convert-shelf-20260917-01).
# lexington-mrf-diversion-gate.html convert shelf reuses the White Box
# hour link (sledge-kincell-lexington-convert-shelf-20260917-01).
# image-drop.html convert shelf reuses the White Box hour link
# (sledge-fleetworkorder-imagedrop-convert-shelf-20260917-01).
# KEEP convert-shelf doors live in VERIFIED_PRODUCT_CHECKOUT. The no-Stripe
# complement is named below so image-drop.html cannot fall back into
# assertNotIn(buy.stripe.com) while still carrying the existing PL.
EXISTING_WHITE_BOX_HOUR_PL = (
    b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07'
)
NO_STRIPE_DOORS = frozenset((
    'feature-tracker.html',
    'gpt-grok-ship-loop.html',
    'grave-card.html',
    'incoming-models.html',
    'lda-receipt.html',
    'listing-registry.html',
))
VERIFIED_PRODUCT_CHECKOUT = {
    'invoice-exception-pack.html': (
        b'https://buy.stripe.com/14A00i84Jdvz36hdxg43S0l',
    ),
    'land.html': (
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
    'keyb.html': (
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
    'builds.html': (
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
    'keys.html': (
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
    'health.html': (
        b'https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b',
        b'https://buy.stripe.com/9B600i98N77b9uFeBk43S0c',
        b'https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d',
        b'https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e',
        b'https://buy.stripe.com/7sYdR8ckZgHLbCN50K43S0y',
        b'https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x',
        b'https://buy.stripe.com/28E9AS70F6378qB2SC43S0w',
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
    'glyphs.html': (
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
    'flipbook.html': (
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
    'insights.html': (
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
    'grounding.html': (
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
    'interconnect.html': (
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
    'image-drop.html': (
        EXISTING_WHITE_BOX_HOUR_PL,
    ),
    'landed-work.html': (
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
    'lexington-mrf-diversion-gate.html': (
        b'https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07',
    ),
}

def https_buy_urls(data: bytes) -> set[bytes]:
    """Exact https://buy.stripe.com/<path> URLs. Does not rewrite http://."""
    return set(re.findall(br'https://buy\.stripe\.com/[A-Za-z0-9_-]+', data))


class BassLargerFixedBatchTest(unittest.TestCase):
    def test_exactly_twenty_doors(self) -> None:
        self.assertEqual(len(TARGETS), 20)
        keep = frozenset(VERIFIED_PRODUCT_CHECKOUT)
        self.assertEqual(set(TARGETS), keep | NO_STRIPE_DOORS)
        self.assertTrue(keep.isdisjoint(NO_STRIPE_DOORS))
        self.assertIn('image-drop.html', keep)
        self.assertNotIn('image-drop.html', NO_STRIPE_DOORS)
        self.assertEqual(
            VERIFIED_PRODUCT_CHECKOUT['image-drop.html'],
            (EXISTING_WHITE_BOX_HOUR_PL,),
        )
        for name in TARGETS:
            data = (ROOT / name).read_bytes()
            with self.subTest(name=name):
                self.assertIn(b"Larger fixed engagements", data)
                self.assertIn(b"diagnostic.html", data)
                self.assertNotIn(b'http://buy.stripe.com/', data.lower())
                expected = VERIFIED_PRODUCT_CHECKOUT.get(name)
                if name in NO_STRIPE_DOORS:
                    self.assertIsNone(expected)
                    self.assertNotIn(b"buy.stripe.com", data)
                    continue
                self.assertIsNotNone(expected)
                for url in expected:
                    self.assertIn(url, data)
                self.assertEqual(https_buy_urls(data), set(expected))

    def test_image_drop_keep_convert_shelf_existing_pl(self) -> None:
        data = (ROOT / 'image-drop.html').read_bytes()
        self.assertIn(EXISTING_WHITE_BOX_HOUR_PL, data)
        self.assertEqual(https_buy_urls(data), {EXISTING_WHITE_BOX_HOUR_PL})
        self.assertNotIn(b'http://buy.stripe.com/', data.lower())
        self.assertIn(
            b'sledge-fleetworkorder-imagedrop-convert-shelf-20260917-01',
            data,
        )
        self.assertIn(b'Buy one White Box hour $250', data)

if __name__ == "__main__":
    unittest.main()
