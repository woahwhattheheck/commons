#!/usr/bin/env python3
"""Hermetic: leftover live-cash doors keep Larger fixed; ingest snippet KEEP."""
from __future__ import annotations

import unittest
from pathlib import Path

import board_ingest
import hub_pages

ROOT = Path(__file__).resolve().parent
DOORS = (
    "annex.html",
    "archive.html",
    "board.html",
    "boards.html",
    "books.html",
    "catering-deposit-rescue.html",
    "ccc-snapshot-toolchain.html",
    "claims.html",
    "claudes.html",
    "court.html",
    "data-license.html",
    "data.html",
    "delta.html",
    "dj-trail.html",
    "entry.html",
    "features.html",
    "federated-ci.html",
    "film.html",
    "first-night.html",
    "fleet-work-order.html",
)
NOTE = "Larger fixed engagements"
H1 = 'href="./diagnostic.html"'
H2 = 'href="./commercial.html"'
SKU1 = "GGUF diagnostic · $12,000 / 10 days"
SKU2 = "White Box pilot · $30,000 / 30 days"


class TypeFunnelDoorsLargerFixedTests(unittest.TestCase):
    def test_hub_pages_live_cash_products_keep_larger_fixed(self) -> None:
        text = hub_pages.LIVE_CASH_PRODUCTS_HTML
        self.assertIn(NOTE, text)
        self.assertIn(H1, text)
        self.assertIn(H2, text)
        self.assertIn(SKU1, text)
        self.assertIn(SKU2, text)
        self.assertNotIn("youtu.be", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn(NOTE, hub_pages.LIVE_CASH_HTML)
        helper = board_ingest.live_cash_html()
        self.assertIn(NOTE, helper)
        self.assertNotIn("buy.stripe.com", helper)

    def test_twenty_leftover_doors_keep_larger_fixed(self) -> None:
        for name in DOORS:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn(NOTE, text)
                self.assertIn(H1, text)
                self.assertIn(H2, text)
                self.assertIn(SKU1, text)
                self.assertIn(SKU2, text)
                self.assertNotIn("youtu.be", text)


if __name__ == "__main__":
    unittest.main()
