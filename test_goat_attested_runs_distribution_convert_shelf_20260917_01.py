#!/usr/bin/env python3
"""goat-attested-runs-distribution-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
attested-runs.html and distribution.html. Do not invent new buy.stripe.com
host paths. Keep Live cash product-page links. Same rails as GOAT
free-sample/humans and Wire tools / Latch annex convert: Autopsy $29 +
White Box hour $250 only. Tip KEEP. Hands off Type agent-triage/control,
Wire live/delta, Latch annex/archive + #15248 fleet, Quill product
heroes, ingest, fat index, #8802.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ATTESTED = ROOT / "attested-runs.html"
DISTRIBUTION = ROOT / "distribution.html"
RECEIPT = ROOT / "p" / "goat-attested-runs-distribution-convert-shelf-20260917-01.md"
COPY_RECEIPT = ROOT / "p" / "goat-attested-runs-distribution-convert-copy-20260917-01.md"

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
    "See what broke in one failed agent run — $29.",
    "One live instrumented hour, white box — $250.",
)
GENERIC_LABELS = (
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
PAGES = (ATTESTED, DISTRIBUTION)


def live_buy_urls(html: str) -> set[str]:
    """Canonical https://buy.stripe.com/<path> identities found in HTML."""
    return {
        f"https://buy.stripe.com/{path}"
        for path in BUY_HOST_PATH.findall(html)
    }


def convert_shelf(html: str) -> str:
    """First-screen Buy now shelf, cut before live-cash."""
    after = html.split('id="buy-now-live-checkout"', 1)[1]
    for marker in ('id="live-cash"', 'id="titanmcp-pad-pointer"', "<main", "<h1"):
        if marker in after:
            after = after.split(marker, 1)[0]
            break
    return after


class TestGoatAttestedRunsDistributionConvertShelf2026091701(unittest.TestCase):
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
                for generic in GENERIC_LABELS:
                    self.assertNotIn(generic, shelf, generic)
                self.assertIn('id="live-cash"', html)
                live_cash = html.split('id="live-cash"', 1)[1]
                live_cash = live_cash.split("</section>", 1)[0]
                self.assertNotIn("buy.stripe.com", live_cash)
                for door in LIVE_CASH_DOORS:
                    self.assertIn(door, html, door)
                nav_at = html.find('class="nav"')
                shelf_at = html.find('id="buy-now-live-checkout"')
                live_cash_at = html.find('id="live-cash"')
                self.assertGreater(nav_at, -1)
                self.assertGreater(shelf_at, nav_at)
                self.assertGreater(live_cash_at, shelf_at)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(
            "id: goat-attested-runs-distribution-convert-shelf-20260917-01",
            text,
        )
        self.assertIn(
            "goat-attested-runs-distribution-convert-shelf-20260917-01",
            text,
        )
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        copy = COPY_RECEIPT.read_text(encoding="utf-8")
        self.assertIn(
            "id: goat-attested-runs-distribution-convert-copy-20260917-01",
            copy,
        )
        for label in BUY_LABELS:
            self.assertIn(label, copy, label)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, copy)
        for name in (
            "attested-runs.html",
            "distribution.html",
            "agent-rescue.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
