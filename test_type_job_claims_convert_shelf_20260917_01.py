#!/usr/bin/env python3
"""type-job-claims-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
job.html and claims.html. Do not invent new buy.stripe.com host paths.
Do not wire the nine-link shelf. Keep Live cash product-page links.
Match avatars.html thin CTA style. Tip KEEP. Hands off Wire authorship/
accordion, Latch 8bit/8walk/annex/archive, Goat mcp-tool-drift/
free-sample/humans, Quill, Type keep-sell/autogtm/action/capabilities/
avatars/clans/commands/cloud-current, Muse, lead spam, PUT ingest, fat
index, #8802.
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import board_ingest
import hub_pages


ROOT = Path(__file__).resolve().parent
JOB = ROOT / "job.html"
CLAIMS = ROOT / "claims.html"
RECEIPT = ROOT / "p" / "type-job-claims-convert-shelf-20260917-01.md"
RENDERER = ROOT / "hub_pages.py"
AVATARS = ROOT / "avatars.html"

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
PAGES = (JOB, CLAIMS)
CITE = "type-job-claims-convert-shelf-20260917-01"
# job.html is thin; claims.html carries session/law/nav chrome before titanmcp.
ABOVE_FOLD_MAX = {
    "job.html": 4500,
    "claims.html": 8000,
}
NINE_LINK_EXCLUDED = (
    "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
    "https://buy.stripe.com/7sYdR8ckZgHLbCN50K43S0y",
    "https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x",
    "https://buy.stripe.com/28E9AS70F6378qB2SC43S0w",
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


class TestTypeJobClaimsConvertShelf2026091701(unittest.TestCase):
    def test_copied_urls_match_avatars_character_exact(self) -> None:
        avatars = AVATARS.read_text(encoding="utf-8")
        self.assertEqual(live_buy_urls(avatars), ALLOWED_LIVE_BUY_URLS)
        found = hub_pages.JOB_CLAIMS_CONVERT_SHELF_HTML
        self.assertEqual(live_buy_urls(found), ALLOWED_LIVE_BUY_URLS)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, avatars)
            self.assertIn(url, found)

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
                self.assertIn('id="live-cash"', html)
                self.assertNotIn("buy.stripe.com", live_cash_slice(html))
                for door in LIVE_CASH_DOORS:
                    self.assertIn(door, html, door)
                self.assertIn("Larger fixed engagements", html)
                self.assertIn("diagnostic.html", html)
                self.assertIn("commercial.html", html)
                nav_or_h1 = max(html.find("<h1"), html.find('class="nav"'))
                shelf_at = html.find('id="buy-now-live-checkout"')
                live_cash_at = html.find('id="live-cash"')
                titan_at = html.find('id="titanmcp-pad-pointer"')
                self.assertGreater(nav_or_h1, -1)
                self.assertGreater(shelf_at, -1)
                self.assertGreater(live_cash_at, shelf_at)
                self.assertGreater(shelf_at, titan_at)
                self.assertLess(
                    shelf_at,
                    ABOVE_FOLD_MAX[page.name],
                    f"{page.name} Buy shelf not above fold / first screen",
                )
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertLess(
                        html.find(url),
                        ABOVE_FOLD_MAX[page.name],
                        f"{page.name} {url} not above fold",
                    )
                for label in BUY_LABELS:
                    self.assertLess(
                        html.find(label),
                        ABOVE_FOLD_MAX[page.name],
                        f"{page.name} {label} not above fold",
                    )
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)
                self.assertIn(".cta{", html)

    def test_rebuild_claims_emits_the_same_existing_buys(self) -> None:
        source = RENDERER.read_text(encoding="utf-8")
        self.assertIn("JOB_CLAIMS_CONVERT_SHELF_HTML", source)
        self.assertIn(CITE, source)
        found = live_buy_urls(hub_pages.JOB_CLAIMS_CONVERT_SHELF_HTML)
        self.assertEqual(found, ALLOWED_LIVE_BUY_URLS)
        self.assertNotIn("buy.stripe.com", hub_pages.LIVE_CASH_PRODUCTS_HTML)
        for label in BUY_LABELS:
            self.assertIn(label, hub_pages.JOB_CLAIMS_CONVERT_SHELF_HTML, label)
        self.assertIn(CITE, hub_pages.JOB_CLAIMS_CONVERT_SHELF_HTML)

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            rows = [
                (
                    "2026-09-17T11:00:00Z",
                    {
                        "id": "type-claims-fixture",
                        "from": "TYPE",
                        "to": "CLAIMS",
                    },
                    "Claim: Convert-shelf fixture\nEvidence: Recorded output",
                )
            ]
            with patch.object(board_ingest, "ROOT", str(tmp)):
                hub_pages.rebuild_claims(board_ingest, rows)
            html = (tmp / "claims.html").read_text(encoding="utf-8")
            self.assertEqual(live_buy_urls(html), ALLOWED_LIVE_BUY_URLS)
            self.assertIn("Buy Autopsy $29", html)
            self.assertIn("Buy one White Box hour $250", html)
            self.assertIn("Buy now", html)
            self.assertIn('class="cta"', html)
            self.assertIn(CITE, html)
            gen_cash = live_cash_slice(html)
            self.assertNotIn("buy.stripe.com", gen_cash)
            self.assertGreater(
                html.find('id="live-cash"'),
                html.find('id="buy-now-live-checkout"'),
            )
            self.assertTrue((tmp / "claims.json").is_file())

    def test_receipt_and_sources_exist(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(f"id: {CITE}", text)
        self.assertIn(CITE, text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        self.assertNotIn("https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b", text)
        for name in (
            "job.html",
            "claims.html",
            "avatars.html",
            "agent-rescue.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)
            self.assertIn(name, text)
        self.assertNotIn("accordion.html", text)
        self.assertNotIn("8bit.html", text)
        self.assertNotIn("free-sample.html", text)
        self.assertNotIn("keep-sell.html", text)
        self.assertNotIn("action.html", text)
        self.assertNotIn("capabilities.html", text)
        self.assertNotIn("commands.html", text)
        self.assertNotIn("cloud-current.html", text)


if __name__ == "__main__":
    unittest.main()
