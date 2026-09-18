#!/usr/bin/env python3
"""latch-annex-archive-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
annex.html and archive.html. Do not invent new buy.stripe.com host
paths. Keep Live cash product-page links. Match tools.html / entry.html
CTA style. Tip KEEP. Hands off Type payment-capability / offer / scope,
Wire tools/toolbench / entry/land, Latch pack / fleet-work-order,
commercial.html, diagnostic.html, ingest, fat index, #8802.
"""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import board_ingest
import hub_pages


ROOT = Path(__file__).resolve().parent
ANNEX = ROOT / "annex.html"
ARCHIVE = ROOT / "archive.html"
RECEIPT = ROOT / "p" / "latch-annex-archive-convert-shelf-20260917-01.md"
RENDERER = ROOT / "hub_pages.py"

ALLOWED_LIVE_BUY_URLS = frozenset(
    {
        "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
        "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
    }
)
BUY_HOST_PATH = re.compile(
    r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
BUY_LABELS = (
    "Buy Autopsy $29",
    "Buy one White Box hour $250",
)
LIVE_CASH_DOORS = (
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
PAGES = (ANNEX, ARCHIVE)


def live_buy_urls(html: str) -> set[str]:
    """Canonical https://buy.stripe.com/<path> identities found in HTML."""
    return {
        f"https://buy.stripe.com/{path}"
        for path in BUY_HOST_PATH.findall(html)
    }


def convert_shelf(html: str) -> str:
    """First-screen Buy now shelf, cut before live-cash."""
    after = html.split('id="buy-now-live-checkout"', 1)[1]
    for marker in ('id="live-cash"', "<main", "<h1"):
        if marker in after:
            after = after.split(marker, 1)[0]
            break
    return after


class TestLatchAnnexArchiveConvertShelf2026091701(unittest.TestCase):
    def test_both_pages_reuse_exactly_the_existing_live_buys(self) -> None:
        for page in PAGES:
            with self.subTest(page=page.name):
                html = page.read_text(encoding="utf-8")
                self.assertIn('id="buy-now-live-checkout"', html)
                self.assertIn("Buy now — live checkout", html)
                self.assertIn('class="cta"', html)
                self.assertIn("data-checkout", html)
                found = live_buy_urls(html)
                self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
                self.assertNotIn("donate.stripe.com", html)
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertIn(url, html)
                shelf = convert_shelf(html)
                for label in BUY_LABELS:
                    self.assertIn(label, shelf, label)
                self.assertIn("latch-annex-archive-convert-shelf-20260917-01", shelf)
                self.assertIn('id="live-cash"', html)
                live_cash = html.split('id="live-cash"', 1)[1]
                live_cash = live_cash.split("</section>", 1)[0]
                self.assertNotIn("buy.stripe.com", live_cash)
                for door in LIVE_CASH_DOORS:
                    self.assertIn(door, html, door)
                self.assertIn("Larger fixed engagements", html)
                self.assertIn("diagnostic.html", html)
                self.assertIn("commercial.html", html)
                nav_or_h1 = html.find("<h1")
                shelf_at = html.find('id="buy-now-live-checkout"')
                live_cash_at = html.find('id="live-cash"')
                self.assertGreater(nav_or_h1, -1)
                self.assertGreater(shelf_at, -1)
                self.assertGreater(live_cash_at, shelf_at)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)

    def test_hub_pages_emits_the_same_existing_buys_on_rebuild(self) -> None:
        source = RENDERER.read_text(encoding="utf-8")
        self.assertIn("ANNEX_ARCHIVE_CONVERT_SHELF_HTML", source)
        self.assertIn("latch-annex-archive-convert-shelf-20260917-01", source)
        found = live_buy_urls(hub_pages.ANNEX_ARCHIVE_CONVERT_SHELF_HTML)
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        self.assertNotIn("buy.stripe.com", hub_pages.LIVE_CASH_PRODUCTS_HTML)
        for label in BUY_LABELS:
            self.assertIn(label, hub_pages.ANNEX_ARCHIVE_CONVERT_SHELF_HTML, label)

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "books.json").write_text("[]", encoding="utf-8")
            (tmp / "hidden.json").write_text("[]", encoding="utf-8")
            rows = [
                (
                    "2026-09-17T08:00:00Z",
                    {
                        "id": "latch-annex-fixture",
                        "from": "LATCH",
                        "to": "TABLE",
                        "lane": "ANNEX",
                    },
                    "Annex convert-shelf fixture",
                )
            ]
            with patch.object(board_ingest, "ROOT", str(tmp)):
                hub_pages.rebuild_lanes(board_ingest, rows)
                hub_pages.rebuild_archive(board_ingest, rows)
            annex = (tmp / "annex.html").read_text(encoding="utf-8")
            archive = (tmp / "archive.html").read_text(encoding="utf-8")
            for html, name in ((annex, "annex.html"), (archive, "archive.html")):
                with self.subTest(rebake=name):
                    self.assertEqual(live_buy_urls(html), ALLOWED_LIVE_BUY_URLS, name)
                    self.assertIn("Buy Autopsy $29", html)
                    self.assertIn("Buy one White Box hour $250", html)
                    self.assertIn('class="cta"', html)
                    gen_cash = html.split('id="live-cash"', 1)[1]
                    gen_cash = gen_cash.split("</section>", 1)[0]
                    self.assertNotIn("buy.stripe.com", gen_cash)
                    self.assertGreater(
                        html.find('id="live-cash"'),
                        html.find('id="buy-now-live-checkout"'),
                    )
            lanes = json.loads((tmp / "lanes.json").read_text(encoding="utf-8"))
            self.assertEqual(lanes["annex"]["n"], 1)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: latch-annex-archive-convert-shelf-20260917-01", text)
        self.assertIn("latch-annex-archive-convert-shelf-20260917-01", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "annex.html",
            "archive.html",
            "agent-rescue.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
