#!/usr/bin/env python3
"""wire-boards-builds-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
boards.html and builds.html. Do not invent new buy.stripe.com host paths.
Keep Live cash product-page links. Match entry.html / live.html CTA style.
Tip KEEP. Hands off Latch annex/archive, Type agent-triage/control (#15492),
Goat free-sample/humans, Quill leftover, Muse, PUT ingest, fat index, #8802.
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import board_ingest
import hub_pages


ROOT = Path(__file__).resolve().parent
BOARDS = ROOT / "boards.html"
BUILDS = ROOT / "builds.html"
RECEIPT = ROOT / "p" / "wire-boards-builds-convert-shelf-20260917-01.md"
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
PRODUCT_PAGES = (
    "agent-rescue.html",
    "commercial.html",
    "diagnostic.html",
)
PAGES = (BOARDS, BUILDS)
CITE = "wire-boards-builds-convert-shelf-20260917-01"


def live_buy_urls(html: str) -> set[str]:
    return {
        f"https://buy.stripe.com/{path}"
        for path in BUY_HOST_PATH.findall(html)
    }


def convert_shelf(html: str) -> str:
    after = html.split('id="buy-now-live-checkout"', 1)[1]
    for marker in ('id="live-cash"', "<main", "<h1"):
        if marker in after:
            after = after.split(marker, 1)[0]
            break
    return after


class TestWireBoardsBuildsConvertShelf2026091701(unittest.TestCase):
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
                self.assertIn(CITE, shelf)
                self.assertIn('id="live-cash"', html)
                live_cash = html.split('id="live-cash"', 1)[1]
                live_cash = live_cash.split("</section>", 1)[0]
                self.assertNotIn("buy.stripe.com", live_cash)
                self.assertIn("agent-rescue.html", html)
                self.assertIn("Larger fixed engagements", html)
                self.assertIn("diagnostic.html", html)
                self.assertIn("commercial.html", html)
                shelf_at = html.find('id="buy-now-live-checkout"')
                live_cash_at = html.find('id="live-cash"')
                self.assertGreater(shelf_at, -1)
                self.assertGreater(live_cash_at, shelf_at)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)
                self.assertIn(".cta{", html)

    def test_product_pages_and_receipt_exist(self) -> None:
        for name in PRODUCT_PAGES:
            self.assertTrue((ROOT / name).is_file(), name)
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(f"id: {CITE}", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        self.assertIn("boards.html", text)
        self.assertIn("builds.html", text)

    def test_ingest_splices_boards_builds_after_remint(self) -> None:
        ingest = INGEST.read_text(encoding="utf-8")
        self.assertIn("def splice_boards_builds_convert_shelf", ingest)
        self.assertIn("splice_boards_builds_convert_shelf()", ingest)
        self.assertIn("BOARDS_BUILDS_CONVERT_SHELF", ingest)
        self.assertIn(CITE, ingest)
        found = live_buy_urls(board_ingest.BOARDS_BUILDS_CONVERT_SHELF)
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertNotIn(CITE, hub)
        ledger = (ROOT / "builds_ledger.py").read_text(encoding="utf-8")
        self.assertNotIn(CITE, ledger)

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
            (tmp / "boards.html").write_text(stub, encoding="utf-8")
            (tmp / "builds.html").write_text(stub, encoding="utf-8")
            self.assertTrue(board_ingest.splice_boards_builds_convert_shelf(root=td))
            self.assertFalse(board_ingest.splice_boards_builds_convert_shelf(root=td))
            for name in ("boards.html", "builds.html"):
                html = (tmp / name).read_text(encoding="utf-8")
                self.assertIn('id="buy-now-live-checkout"', html)
                self.assertEqual(live_buy_urls(html), ALLOWED_LIVE_BUY_URLS)
                for label in BUY_LABELS:
                    self.assertIn(label, html, label)
                self.assertIn(".cta{", html)
                self.assertIn(CITE, html)
                live_cash = html.split('id="live-cash"', 1)[1]
                live_cash = live_cash.split("</section>", 1)[0]
                self.assertNotIn("buy.stripe.com", live_cash)
                self.assertGreater(
                    html.find('id="live-cash"'),
                    html.find('id="buy-now-live-checkout"'),
                )

    def test_boards_shelf_survives_hub_rebuild_splice(self) -> None:
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

            hub_pages.rebuild_boards(_Mod(), {"open": [], "done": [], "receipts": 0})
            rebuilt = (tmp / "boards.html").read_text(encoding="utf-8")
            self.assertNotIn('id="buy-now-live-checkout"', rebuilt)
            self.assertTrue(board_ingest.splice_boards_builds_convert_shelf(root=td))
            restored = (tmp / "boards.html").read_text(encoding="utf-8")
            self.assertIn('id="buy-now-live-checkout"', restored)
            self.assertEqual(live_buy_urls(restored), ALLOWED_LIVE_BUY_URLS)
            self.assertIn(CITE, restored)
            self.assertGreater(
                restored.find('id="live-cash"'),
                restored.find('id="buy-now-live-checkout"'),
            )


if __name__ == "__main__":
    unittest.main()
