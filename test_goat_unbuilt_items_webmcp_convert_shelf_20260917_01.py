#!/usr/bin/env python3
"""goat-unbuilt-items-webmcp-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
unbuilt-items.html and webmcp.html with DeepSeek convert copy.
Do not invent new buy.stripe.com host paths. Keep Live cash product-page
links. Same rails as GOAT #15572 distro/paperwork-included DeepSeek copy:
Autopsy $29 + White Box hour $250 only. Tip KEEP. Hands off Type
agent-triage/control/action/capabilities/commands/cloud-current/avatars/clans/keep-sell/autogtm,
Type #15575 trust.html/topics.html, Wire live/delta/boards/builds/arbitrage/attested-inference/authorship/accordion,
Latch annex/archive #15248, 8bit/8walk, Quill wake/world/data/weather heroes,
ingest, fat index, #8802. head.html already has Buy CTAs — do not remint.
"""
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
UNBUILT = ROOT / "unbuilt-items.html"
WEBMCP = ROOT / "webmcp.html"
RECEIPT = ROOT / "p" / "goat-unbuilt-items-webmcp-convert-shelf-20260917-01.md"
AGENT_RESCUE = ROOT / "agent-rescue.html"
COMMERCIAL = ROOT / "commercial.html"

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
PAGES = (UNBUILT, WEBMCP)
CITE = "goat-unbuilt-items-webmcp-convert-shelf-20260917-01"
ALLOWLIST_PAGES = ("unbuilt-items.html", "webmcp.html")
UNLOCK_CHECKOUT = "https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04"


def _load_host(name: str):
    path = ROOT / "host" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(
        f"goat_unbuilt_items_webmcp_{name}", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


payment_capability = _load_host("payment_capability")


def live_buy_urls(html: str) -> set[str]:
    """Canonical https://buy.stripe.com/<path> identities found in HTML."""
    return {
        f"https://buy.stripe.com/{path}"
        for path in BUY_HOST_PATH.findall(html)
    }


def convert_shelf(html: str) -> str:
    """First-screen Buy now shelf, cut before hero / live-cash."""
    after = html.split('id="buy-now-live-checkout"', 1)[1]
    for marker in ("<h1", 'id="titanmcp-pad-pointer"', "<main", 'id="live-cash"'):
        if marker in after:
            after = after.split(marker, 1)[0]
            break
    return after


def live_cash_slice(html: str) -> str:
    after = html.split('id="live-cash"', 1)[1]
    if "</section>" in after:
        return after.split("</section>", 1)[0]
    if "</p>" in after:
        return after.split("</p>", 1)[0]
    return after[:900]


class TestGoatUnbuiltItemsWebmcpConvertShelf2026091701(unittest.TestCase):
    def test_head_product_pages_still_own_the_exact_urls(self) -> None:
        autopsy = AGENT_RESCUE.read_text(encoding="utf-8")
        commercial = COMMERCIAL.read_text(encoding="utf-8")
        self.assertIn(
            "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
            autopsy,
        )
        self.assertIn(
            "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
            commercial,
        )

    def test_both_pages_reuse_exactly_the_existing_live_buys(self) -> None:
        for page in PAGES:
            with self.subTest(page=page.name):
                html = page.read_text(encoding="utf-8")
                self.assertIn('id="buy-now-live-checkout"', html)
                self.assertIn("Buy now — live checkout", html)
                self.assertIn('class="cta"', html)
                self.assertIn("data-checkout", html)
                self.assertIn(".cta{", html)
                found = live_buy_urls(html)
                self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
                self.assertNotIn("donate.stripe.com", html)
                self.assertNotIn(UNLOCK_CHECKOUT, html)
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertIn(url, html)
                shelf = convert_shelf(html)
                for label in BUY_LABELS:
                    self.assertIn(label, shelf, label)
                for generic in GENERIC_LABELS:
                    self.assertNotIn(generic, shelf, generic)
                self.assertIn(CITE, shelf)
                self.assertIn('id="live-cash"', html)
                self.assertNotIn("buy.stripe.com", live_cash_slice(html))
                for door in LIVE_CASH_DOORS:
                    self.assertIn(door, html, door)
                self.assertIn("diagnostic.html", html)
                self.assertIn("commercial.html", html)
                self.assertIn("Larger fixed engagements", html)
                nav_at = html.find('class="nav"')
                shelf_at = html.find('id="buy-now-live-checkout"')
                live_cash_at = html.find('id="live-cash"')
                h1_at = html.find("<h1")
                self.assertGreater(nav_at, -1)
                self.assertGreater(shelf_at, nav_at)
                self.assertGreater(live_cash_at, shelf_at)
                self.assertGreater(h1_at, shelf_at)
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)

    def test_receipt_and_payment_capability_allowlist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(f"id: {CITE}", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        for label in BUY_LABELS:
            self.assertIn(label, text, label)
        self.assertIn("unbuilt-items.html", text)
        self.assertIn("webmcp.html", text)
        for name in ALLOWLIST_PAGES:
            allowed = payment_capability.CONVERT_SHELF_LIVE_BUYS[name]
            self.assertEqual(allowed, ALLOWED_LIVE_BUY_URLS)
            self.assertIn(name, payment_capability.PUBLIC_HTML)
            page_html = (ROOT / name).read_text(encoding="utf-8")
            self.assertEqual(
                payment_capability.html_stripe_url_errors(name, page_html),
                [],
            )
            forged = page_html.replace(
                "https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g",
                "https://buy.stripe.com/not-a-canonical-link",
                1,
            )
            self.assertEqual(
                payment_capability.html_stripe_url_errors(name, forged),
                [
                    "%s convert shelf must reuse exactly "
                    "the existing live buy.stripe.com URLs" % name
                ],
            )


if __name__ == "__main__":
    unittest.main()
