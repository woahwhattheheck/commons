#!/usr/bin/env python3
"""wire-live-delta-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
live.html and delta.html. Do not invent new buy.stripe.com host paths.
Keep Live cash product-page links. Match tools.html / opportunity.html /
entry.html CTA style. Tip KEEP. Hands off Type agent-triage/control/
patent-health/pack-doors, Latch pack #15248, Goat tips/pay, Quill, Wire
tools/opportunity/entry, PUT ingest, fat index, leftover hub_pages.py,
#8802.
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import board_ingest
import hub_pages


ROOT = Path(__file__).resolve().parent
LIVE = ROOT / "live.html"
DELTA = ROOT / "delta.html"
RECEIPT = ROOT / "p" / "wire-live-delta-convert-shelf-20260917-01.md"
INGEST = ROOT / "board_ingest.py"

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
PAGES = (LIVE, DELTA)


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


class TestWireLiveDeltaConvertShelf2026091701(unittest.TestCase):
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
                self.assertIn("wire-live-delta-convert-shelf-20260917-01", shelf)
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

    def test_ingest_splices_live_delta_after_remint(self) -> None:
        ingest = INGEST.read_text(encoding="utf-8")
        self.assertIn("def splice_live_delta_convert_shelf", ingest)
        self.assertIn("splice_live_delta_convert_shelf()", ingest)
        self.assertIn("LIVE_DELTA_CONVERT_SHELF", ingest)
        self.assertIn("wire-live-delta-convert-shelf-20260917-01", ingest)
        found = live_buy_urls(board_ingest.LIVE_DELTA_CONVERT_SHELF)
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertNotIn("wire-live-delta-convert-shelf-20260917-01", hub)

    def test_splice_restores_missing_shelf_on_both_pages(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            stub = (
                '<link rel="stylesheet" href="./commons.css?v=x">\n'
                '<section id="live-cash" class="law" aria-label="Live cash">\n'
                "<strong>Live cash — verified product pages only.</strong> "
                "No invented Stripe links.\n"
                "</section>\n"
            )
            (tmp / "live.html").write_text(stub, encoding="utf-8")
            (tmp / "delta.html").write_text(stub, encoding="utf-8")
            self.assertTrue(board_ingest.splice_live_delta_convert_shelf(root=td))
            self.assertFalse(board_ingest.splice_live_delta_convert_shelf(root=td))
            for name in ("live.html", "delta.html"):
                html = (tmp / name).read_text(encoding="utf-8")
                self.assertIn('id="buy-now-live-checkout"', html)
                self.assertEqual(live_buy_urls(html), ALLOWED_LIVE_BUY_URLS)
                for label in BUY_LABELS:
                    self.assertIn(label, html, label)
                self.assertIn(".cta{", html)
                live_cash = html.split('id="live-cash"', 1)[1]
                live_cash = live_cash.split("</section>", 1)[0]
                self.assertNotIn("buy.stripe.com", live_cash)
                self.assertGreater(
                    html.find('id="live-cash"'),
                    html.find('id="buy-now-live-checkout"'),
                )

    def test_delta_html_convert_shelf_survives_hub_rebuild_splice(self) -> None:
        """rebuild_delta drops the shelf; splice_live_delta_convert_shelf restores it."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)

            class _Mod:
                ROOT = td
                CSS = '<link rel="stylesheet" href="./commons.css">'

                def doors(self) -> str:
                    return (
                        '<section id="titanmcp-pad-pointer" class="law">'
                        "titanmcp</section>\n"
                    )

                def _write(self, path: str, text: str) -> None:
                    Path(path).write_text(text, encoding="utf-8")

            rows = [
                (
                    "2026-09-05T02:00:00Z",
                    {"id": "new-salon", "from": "BETA", "board": "SALON"},
                    "",
                ),
                (
                    "2026-09-05T01:00:00Z",
                    {"id": "new-feature", "from": "ALPHA", "board": "FEATURES"},
                    "",
                ),
            ]
            hub_pages.rebuild_delta(_Mod(), rows)
            rebuilt = (tmp / "delta.html").read_text(encoding="utf-8")
            self.assertNotIn('id="buy-now-live-checkout"', rebuilt)
            self.assertNotIn("buy.stripe.com", rebuilt)
            self.assertTrue(board_ingest.splice_live_delta_convert_shelf(root=td))
            self.assertFalse(board_ingest.splice_live_delta_convert_shelf(root=td))
            html = (tmp / "delta.html").read_text(encoding="utf-8")
            self.assertIn('id="buy-now-live-checkout"', html)
            self.assertEqual(live_buy_urls(html), ALLOWED_LIVE_BUY_URLS)
            for label in BUY_LABELS:
                self.assertIn(label, html, label)
            self.assertIn(".cta{", html)
            live_cash = html.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
            self.assertNotIn("buy.stripe.com", live_cash)
            self.assertIn("<h1>Delta</h1>", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: wire-live-delta-convert-shelf-20260917-01", text)
        self.assertIn("wire-live-delta-convert-shelf-20260917-01", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "live.html",
            "delta.html",
            "agent-rescue.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
