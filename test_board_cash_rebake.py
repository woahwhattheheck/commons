#!/usr/bin/env python3
"""Keep board product links through real publisher rebuilds."""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import board_ingest
import hub_pages


PUBLISHERS = {
    "annex.html": hub_pages.rebuild_lanes,
    "archive.html": hub_pages.rebuild_archive,
    "books.html": hub_pages.rebuild_books,
    "claims.html": hub_pages.rebuild_claims,
}
PRODUCTS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_FIXED = (
    "diagnostic.html",
    "commercial.html",
)
# LIVE_CASH_PRODUCTS_HTML lists $199/$199 then Larger fixed. Exact href
# order is the rebuild contract: extras would hide a remint wipe.
CASH_HREFS = tuple("./" + name for name in PRODUCTS + LARGER_FIXED)


class BoardCashRebakeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.rows = [
            ("2026-09-01T12:00:00Z", {"id": "rill-annex", "from": "RILL", "to": "TABLE", "lane": "ANNEX"}, "Annex entry"),
            ("2026-09-01T13:00:00Z", {"id": "rill-book", "from": "RILL", "to": "TABLE", "kind": "BOOK"}, "Chapter one"),
            ("2026-09-02T12:00:00Z", {"id": "rill-claim", "from": "RILL", "to": "CLAIMS"}, "Claim: Published fixture\nEvidence: Recorded output"),
        ]
        (self.root / "books.json").write_text(json.dumps([{"title": "Rill shelf", "chapters": ["rill-book", "rill-hidden"]}]), encoding="utf-8")
        (self.root / "hidden.json").write_text('["rill-hidden"]', encoding="utf-8")

    def bake(self, name, rows=None):
        with patch.object(board_ingest, "ROOT", str(self.root)):
            PUBLISHERS[name](board_ingest, self.rows if rows is None else rows)
        return (self.root / name).read_text(encoding="utf-8")

    def assert_cash(self, text, convert_shelf=False):
        self.assertEqual(text.count('id="live-cash"'), 1)
        section = re.search(r'<section\b[^>]*\bid="live-cash"[^>]*>.*?</section>', text, re.S).group()
        self.assertEqual(re.findall(r'href="([^\"]+)"', section), list(CASH_HREFS))

        self.assertIn("$199 dealer diagnostic", section)
        self.assertIn("Larger fixed engagements", section)
        self.assertIn("GGUF diagnostic · $12,000 / 10 days", section)
        self.assertIn("White Box pilot · $30,000 / 30 days", section)
        self.assertNotIn("tools-cash.html", text)
        self.assertNotIn("buy.stripe.com", section)
        if convert_shelf:
            self.assertIn('id="buy-now-live-checkout"', text)

            self.assertIn("https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07", text)
            self.assertGreater(
                text.find('id="live-cash"'),
                text.find('id="buy-now-live-checkout"'),
            )
        else:
            self.assertNotIn("buy.stripe.com", text)

    def repeated_bake(self, name):
        first = self.bake(name)
        self.assert_cash(
            first,
            convert_shelf=name in ("annex.html", "archive.html", "books.html", "claims.html"),
        )
        self.assertEqual(self.bake(name), first)
        self.assertIn('id="trust-through-proof"', first)
        return first

    def test_annex_rebuild_retains_products_form_and_lane_data(self):
        text = self.repeated_bake("annex.html")
        self.assertIn('id="say"', text)
        self.assertIn('data-lane="ANNEX"', text)
        self.assertIn('src="./board.js?', text)
        lanes = json.loads((self.root / "lanes.json").read_text(encoding="utf-8"))
        self.assertEqual(lanes["annex"]["n"], 1)
        self.assertEqual(lanes["annex"]["posts"][0]["id"], "rill-annex")

    def test_archive_rebuild_retains_products_and_day_pages(self):
        text = self.repeated_bake("archive.html")
        self.assertIn('href="./d/2026-09-01.html"', text)
        self.assertIn('href="./d/2026-09-02.html"', text)
        day = (self.root / "d" / "2026-09-01.html").read_text(encoding="utf-8")
        self.assertIn("Chapter one", day)
        self.assertIn('href="../p/rill-book.html"', day)

    def test_books_rebuild_retains_products_and_visible_chapters(self):
        text = self.repeated_bake("books.html")
        self.assertIn("Rill shelf", text)
        self.assertIn('href="./p/rill-book.html"', text)
        self.assertIn("Chapter one", text)
        self.assertNotIn("rill-hidden", text)
        self.assertIn('id="say"', text)

    def test_claims_rebuild_retains_products_evidence_and_status(self):
        text = self.repeated_bake("claims.html")
        self.assertIn('href="./p/rill-claim.html"', text)
        self.assertIn("Recorded output", text)
        self.assertIn('data-to="CLAIMS"', text)
        claims = json.loads((self.root / "claims.json").read_text(encoding="utf-8"))["claims"]
        claim = next(row for row in claims if row["id"] == "rill-claim")
        self.assertEqual(claim["status"], "OPEN")

    def test_empty_rebuild_replaces_stale_pages_and_preserves_products(self):
        for name in PUBLISHERS:
            with self.subTest(page=name):
                self.bake(name)
                (self.root / name).write_text("stale published output", encoding="utf-8")
                (self.root / "books.json").write_text("[]", encoding="utf-8")
                text = self.bake(name, [])
                self.assert_cash(
                    text,
                    convert_shelf=name in ("annex.html", "archive.html", "books.html", "claims.html"),
                )
                self.assertNotIn("stale published output", text)
                self.assertNotIn("rill-claim", text)
                self.assertNotIn("rill-book", text)

    def test_existing_feature_catalog_variant_stays_available(self):
        self.bake("annex.html")
        text = (self.root / "features.html").read_text(encoding="utf-8")
        self.assertEqual(text.count('id="live-cash"'), 1)
        for name in PRODUCTS + LARGER_FIXED:
            self.assertIn('href="./%s"' % name, text)
        self.assertIn("Larger fixed engagements", text)
        self.assertIn('href="./tools-cash.html"', text)
        self.assertIn('href="./commerce.html"', text)

    def test_live_cash_products_html_keeps_larger_fixed_hrefs(self):
        text = hub_pages.LIVE_CASH_PRODUCTS_HTML
        section = re.search(r'<section\b[^>]*\bid="live-cash"[^>]*>.*?</section>', text, re.S).group()
        self.assertEqual(re.findall(r'href="([^\"]+)"', section), list(CASH_HREFS))
        self.assertIn("Larger fixed engagements", section)
        self.assertNotIn("buy.stripe.com", section)
        self.assertNotIn("youtu.be", section)


if __name__ == "__main__":
    unittest.main()
