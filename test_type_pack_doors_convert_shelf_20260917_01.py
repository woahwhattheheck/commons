#!/usr/bin/env python3
"""type-pack-doors-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Link URLs onto what-a-pack-is.html,
pack-is-ready-to-run.html, and pack-quality-tier.html. Copy the
payment-capability.html Buy now shelf (same nine URLs, same labels,
same section id). Do not invent new buy.stripe.com host paths. Tip KEEP
relative #live-cash doors stay. Hands off tools.html, toolbench.html,
Latch #15248, Goat tips/titan-hour/agent-ops/mcp/invoice, Quill hero
converts, Type prior convert chain, and #8802.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WHAT = ROOT / "what-a-pack-is.html"
READY = ROOT / "pack-is-ready-to-run.html"
TIER = ROOT / "pack-quality-tier.html"
PAYMENT = ROOT / "payment-capability.html"
RECEIPT = ROOT / "p" / "type-pack-doors-convert-shelf-20260917-01.md"

ALLOWED_LIVE_BUY_URLS = (
    "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
    "https://buy.stripe.com/7sYdR8ckZgHLbCN50K43S0y",
    "https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x",
    "https://buy.stripe.com/28E9AS70F6378qB2SC43S0w",
    "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
)
ALLOWED_LIVE_BUY_URL_SET = frozenset(ALLOWED_LIVE_BUY_URLS)
BUY_HOST_PATH = re.compile(
    r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
SHELF_LABELS = (
    ("Dealer Service Lead Rescue", "$199"),
    ("Referral Intake Completeness", "$199"),
    ("Repair Booking Preflight", "$199"),
    ("Plant Downtime Handoff", "$199"),
    ("Hotel room-turn", "$2,500"),
    ("Late-cancel / no-show", "$3,500"),
    ("Chargeback Evidence Readiness", "$4,000"),
    ("White Box hour", "$250"),
)
RELATIVE_DOORS = (
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
    "./hotel-room-turn-evidence.html",
    "./late-cancel-noshow-fee-leakage.html",
    "./chargeback-evidence-readiness.html",
    "./diagnostic.html",
    "./commercial.html",
)
LIVE_CASH_DOORS = (
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
)
PAGES = (WHAT, READY, TIER)
LI_RE = re.compile(r"<li>.*?</li>", re.DOTALL)


def live_buy_urls(html: str) -> set[str]:
    """Canonical https://buy.stripe.com/<path> identities found in HTML."""
    return {
        f"https://buy.stripe.com/{path}"
        for path in BUY_HOST_PATH.findall(html)
    }


def convert_shelf(html: str) -> str:
    """First-screen Buy now shelf, cut before live-cash / titanmcp."""
    after = html.split('id="buy-now-live-checkout"', 1)[1]
    for marker in ('id="live-cash"', 'id="titanmcp-pad-pointer"', 'id="digit-note"'):
        if marker in after:
            after = after.split(marker, 1)[0]
            break
    return after


def shelf_list_items(html: str) -> list[str]:
    """Ordered <li> rows from the Buy now shelf."""
    return LI_RE.findall(convert_shelf(html))


class TestTypePackDoorsConvertShelf2026091701(unittest.TestCase):
    def test_all_three_html_files_reuse_exactly_the_existing_live_buys(self) -> None:
        source_items = shelf_list_items(PAYMENT.read_text(encoding="utf-8"))
        self.assertEqual(len(source_items), 9)
        for page in PAGES:
            with self.subTest(page=page.name):
                html = page.read_text(encoding="utf-8")
                self.assertIn('id="buy-now-live-checkout"', html)
                self.assertIn("Buy now — live checkout", html)
                found = live_buy_urls(html)
                self.assertEqual(found, ALLOWED_LIVE_BUY_URL_SET)
                self.assertNotIn("donate.stripe.com", html)
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertIn(url, html)
                shelf = convert_shelf(html)
                nav_at = html.find('class="nav"')
                shelf_at = html.find('id="buy-now-live-checkout"')
                live_cash_at = html.find('id="live-cash"')
                titan_at = html.find('id="titanmcp-pad-pointer"')
                self.assertGreater(nav_at, -1)
                self.assertGreater(shelf_at, nav_at)
                self.assertGreater(live_cash_at, shelf_at)
                self.assertGreater(titan_at, shelf_at)
                self.assertEqual(shelf_list_items(html), source_items)
                for name, amount in SHELF_LABELS:
                    self.assertIn(name, shelf, name)
                    self.assertIn(amount, shelf, amount)
                for door in RELATIVE_DOORS:
                    self.assertIn(door, html, door)
                live_cash = html[live_cash_at:]
                for door in LIVE_CASH_DOORS:
                    self.assertIn(door, live_cash, door)
                self.assertIn('id="live-cash"', html)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: type-pack-doors-convert-shelf-20260917-01", text)
        self.assertIn("type-pack-doors-convert-shelf-20260917-01", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for name in (
            "what-a-pack-is.html",
            "pack-is-ready-to-run.html",
            "pack-quality-tier.html",
            "dealer-service-lead-rescue.html",
            "referral-intake-completeness.html",
            "repair-booking-preflight.html",
            "plant-downtime-handoff.html",
            "hotel-room-turn-evidence.html",
            "late-cancel-noshow-fee-leakage.html",
            "chargeback-evidence-readiness.html",
            "commercial.html",
            "diagnostic.html",
            "payment-capability.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
