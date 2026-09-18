#!/usr/bin/env python3
"""type-panel-pixel-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
panel.html and pixel.html. Thin shelf only: White Box
hour $250. Copy character-exact from avatars.html. Do not invent new
buy.stripe.com host paths. Do not wire the nine-link shelf. Keep Live
cash product-page links. Match avatars.html thin CTA style. Tip KEEP.
Hands off look/loop; Latch job/pad/face/film/head/keyb/nojs/post; Wire
authorship/accordion/arbitrage/attested-inference/live/delta/boards/
builds/entry/land; Goat free-sample/humans/attested-runs/distribution/
mcp-tool-drift/claude-paste/failed/task-forge/subzero-*/data-license/
gemini-mcp; Quill hero converts; TYPE shipped keep-sell/autogtm/action/
capabilities/avatars/clans/commands/cloud-current/claims/features;
plug.html; wire.html. Muse, lead spam, PUT ingest, fat index, #8802.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PANEL = ROOT / "panel.html"
PIXEL = ROOT / "pixel.html"
RECEIPT = ROOT / "p" / "type-panel-pixel-convert-shelf-20260917-01.md"

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
PAGES = (PANEL, PIXEL)
CITE = "type-panel-pixel-convert-shelf-20260917-01"
ABOVE_FOLD_MAX = 4500
NINE_LINK_EXCLUDED = (
    "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
    "https://buy.stripe.com/7sYdR8ckZgHLbCN50K43S0y",
    "https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x",
    "https://buy.stripe.com/28E9AS70F6378qB2SC43S0w",
)
FENCED_PAGES = (
    "look.html",
    "loop.html",
    "job.html",
    "pad.html",
    "face.html",
    "film.html",
    "head.html",
    "keyb.html",
    "nojs.html",
    "post.html",
    "authorship.html",
    "accordion.html",
    "arbitrage.html",
    "attested-inference.html",
    "live.html",
    "delta.html",
    "boards.html",
    "builds.html",
    "entry.html",
    "land.html",
    "plug.html",
    "wire.html",
    "keep-sell.html",
    "autogtm.html",
    "action.html",
    "capabilities.html",
    "avatars.html",
    "clans.html",
    "commands.html",
    "cloud-current.html",
    "claims.html",
    "features.html",
    "free-sample.html",
    "humans.html",
    "wake.html",
)


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


def live_cash_slice(html: str) -> str:
    after = html.split('id="live-cash"', 1)[1]
    if "</section>" in after:
        return after.split("</section>", 1)[0]
    if "</p>" in after:
        return after.split("</p>", 1)[0]
    return after


class TestTypePanelPixelConvertShelf2026091701(unittest.TestCase):
    def test_both_pages_reuse_exactly_the_existing_live_buys(self) -> None:
        for page in PAGES:
            with self.subTest(page=page.name):
                html = page.read_text(encoding="utf-8")
                self.assertIn('id="buy-now-live-checkout"', html)
                self.assertIn("Buy now — live checkout", html)
                self.assertIn("Buy now", html)
                self.assertIn('class="cta"', html)
                self.assertIn("data-checkout", html)
                found = live_buy_urls(html)
                self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
                self.assertNotIn("donate.stripe.com", html)
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertIn(url, html)
                    self.assertEqual(html.count(url), 1, url)
                for url in NINE_LINK_EXCLUDED:
                    self.assertNotIn(url, html, url)
                shelf = convert_shelf(html)
                for label in BUY_LABELS:
                    self.assertIn(label, shelf, label)
                self.assertIn(CITE, shelf)
                self.assertIn("Tip KEEP", shelf)
                self.assertIn("#8802 off", shelf)
                self.assertIn('id="live-cash"', html)
                self.assertNotIn("buy.stripe.com", live_cash_slice(html))
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
                self.assertLess(
                    shelf_at,
                    ABOVE_FOLD_MAX,
                    f"{page.name} Buy shelf not above fold / first screen",
                )
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertLess(
                        html.find(url),
                        ABOVE_FOLD_MAX,
                        f"{page.name} {url} not above fold",
                    )
                for label in BUY_LABELS:
                    self.assertLess(
                        html.find(label),
                        ABOVE_FOLD_MAX,
                        f"{page.name} {label} not above fold",
                    )
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)
                self.assertIn(".cta{", html)

    def test_fenced_pages_do_not_carry_this_cite(self) -> None:
        for name in FENCED_PAGES:
            path = ROOT / name
            with self.subTest(page=name):
                self.assertTrue(path.is_file(), name)
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(CITE, text)

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(f"id: {CITE}", text)
        self.assertIn(CITE, text)
        self.assertIn("Tip KEEP", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        self.assertNotIn("https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b", text)
        for name in (
            "panel.html",
            "pixel.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)
            self.assertIn(name, text)
        self.assertNotIn("look.html", text)
        self.assertNotIn("loop.html", text)
        self.assertNotIn("nojs.html", text)
        self.assertNotIn("post.html", text)
        self.assertNotIn("job.html", text)
        self.assertNotIn("pad.html", text)
        self.assertNotIn("face.html", text)
        self.assertNotIn("film.html", text)
        self.assertNotIn("head.html", text)
        self.assertNotIn("keyb.html", text)
        self.assertNotIn("plug.html", text)
        self.assertNotIn("wire.html", text)
        self.assertNotIn("keep-sell.html", text)
        self.assertNotIn("autogtm.html", text)
        self.assertNotIn("action.html", text)
        self.assertNotIn("clans.html", text)
        self.assertNotIn("commands.html", text)
        self.assertNotIn("cloud-current.html", text)
        self.assertNotIn("claims.html", text)
        self.assertNotIn("features.html", text)
        self.assertNotIn("free-sample.html", text)
        self.assertNotIn("wake.html", text)


if __name__ == "__main__":
    unittest.main()
