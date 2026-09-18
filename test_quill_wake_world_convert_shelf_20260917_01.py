#!/usr/bin/env python3
"""quill-wake-world-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
wake.html and world.html. Do not invent new buy.stripe.com host paths.
Keep Live cash product-page links. Match Wire entry/land + live/delta
CTA style. Tip KEEP. Hands off Type agent-triage/control/patent-health/
pack-doors, Wire live/delta/entry/land/tools/boards-builds unpaid,
Latch annex/archive/pack #15248, Goat free-sample/humans/commerce tip/
tips/titan-hour/pay/owner-now, Quill hero converts through #15399,
#8802, invent Stripe, lead spam.
"""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

import hub_pages


ROOT = Path(__file__).resolve().parent
WAKE = ROOT / "wake.html"
WORLD = ROOT / "world.html"
RECEIPT = ROOT / "p" / "quill-wake-world-convert-shelf-20260917-01.md"
RENDERER = ROOT / "hub_pages.py"

ALLOWED_LIVE_BUY_URLS = frozenset(
    {
        "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
    }
)
BUY_HOST_PATH = re.compile(
    r"https?://buy\.stripe\.com/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
BUY_LABELS = (
    "Buy one White Box hour $250",
)
LIVE_CASH_DOORS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
PAGES = (WAKE, WORLD)
CLAIM = "quill-wake-world-convert-shelf-20260917-01"


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


class TestQuillWakeWorldConvertShelf2026091701(unittest.TestCase):
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
                self.assertIn(CLAIM, shelf)
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

    def test_renderer_constants_emit_the_same_existing_buys(self) -> None:
        source = RENDERER.read_text(encoding="utf-8")
        self.assertIn("WAKE_WORLD_CONVERT_SHELF_HTML", source)
        self.assertIn('id="buy-now-live-checkout"', hub_pages.WAKE_WORLD_CONVERT_SHELF_HTML)

        self.assertIn("Buy one White Box hour $250", hub_pages.WAKE_WORLD_CONVERT_SHELF_HTML)
        self.assertIn(CLAIM, hub_pages.WAKE_WORLD_CONVERT_SHELF_HTML)
        found = live_buy_urls(hub_pages.WAKE_WORLD_CONVERT_SHELF_HTML)
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        self.assertNotIn("buy.stripe.com", hub_pages.LIVE_CASH_PRODUCTS_HTML)
        self.assertIn(
            "WAKE_WORLD_CONVERT_SHELF_HTML + LIVE_CASH_PRODUCTS_HTML + body",
            source,
        )

    def test_rebuild_wake_and_world_emit_shelf(self) -> None:
        class _Mod:
            ROOT = ""
            CSS = '<link rel="stylesheet" href="./commons.css">'

            def doors(self):
                return '<p class="nav">nav</p>'

            def _read(self, path):
                return Path(path).read_text(encoding="utf-8")

            def _write(self, path, text):
                Path(path).write_text(text, encoding="utf-8")

            def inject_trust_doctrine(self, text):
                return text

        with tempfile.TemporaryDirectory() as tmp:
            mod = _Mod()
            mod.ROOT = tmp
            Path(tmp, "wake.json").write_text(
                json.dumps({"note": "n", "n": 0, "requests": []}) + "\n",
                encoding="utf-8",
            )
            Path(tmp, "world.json").write_text(
                json.dumps({"n": 0, "items": []}) + "\n",
                encoding="utf-8",
            )
            hub_pages.rebuild_wake(mod, [])
            hub_pages.rebuild_world(mod, [])
            for name in ("wake.html", "world.html"):
                html = Path(tmp, name).read_text(encoding="utf-8")
                with self.subTest(page=name):
                    self.assertIn('id="buy-now-live-checkout"', html)
                    self.assertEqual(live_buy_urls(html), ALLOWED_LIVE_BUY_URLS)
                    self.assertIn(CLAIM, html)
                    shelf_at = html.find('id="buy-now-live-checkout"')
                    live_at = html.find('id="live-cash"')
                    self.assertGreater(live_at, shelf_at)

    def test_receipt_pad_exists(self) -> None:
        self.assertTrue(RECEIPT.is_file(), RECEIPT)
        body = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(CLAIM, body)
        self.assertIn("wake.html", body)
        self.assertIn("world.html", body)
        self.assertIn("4gM9AS3Ot8bfeOZ78S43S0g", body)
        self.assertIn("8x27sK2Kp3UZ9uF2SC43S07", body)


if __name__ == "__main__":
    unittest.main()
