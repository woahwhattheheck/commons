#!/usr/bin/env python3
"""sledge-kincell-lexington-convert-shelf-20260917-01 — convert shelves.

Wire EXISTING live Stripe Payment Links as first-screen Buy CTAs on
kincell-rtp-qc-release-bridge-lims.html and lexington-mrf-diversion-gate.html. Thin shelf only: White Box hour $250. Copy character-exact from avatars.html. Do not
invent new buy.stripe.com host paths. Do not wire the nine-link shelf.
Keep Live cash product-page links. Match avatars.html thin CTA style.
Tip KEEP. HTTPS-exact enroll. Hands off already-shelved convert pairs;
Type observatory/tabletop + priors; Latch writing/cweather + priors;
Goat visual/titanmcp; ANVIL open-door/interconnect + owner-now-revenue/
paid-opportunities; plug.html; wire.html; Muse, lead spam, PUT ingest,
fat index, #8802.
"""
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
KINCELL = ROOT / "kincell-rtp-qc-release-bridge-lims.html"
LEXINGTON = ROOT / "lexington-mrf-diversion-gate.html"
RECEIPT = ROOT / "p" / "sledge-kincell-lexington-convert-shelf-20260917-01.md"

ALLOWED_LIVE_BUY_URLS = frozenset(
    {
        "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
    }
)
BUY_HTTPS_URL = re.compile(r"https://buy\.stripe\.com/[A-Za-z0-9_-]+")
HTTP_BUY_DUP = re.compile(r"http://buy\.stripe\.com/", re.IGNORECASE)
HTTP_DUP_HREF = "http://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07"
BUY_LABELS = (
    "Buy one White Box hour $250",
)
LIVE_CASH_DOORS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
# Per-page extra live-cash markers that must survive the shelf insert.
LIVE_CASH_EXTRA = {
    "kincell-rtp-qc-release-bridge-lims.html": (
        "Live cash",
    ),
    "lexington-mrf-diversion-gate.html": (
        "Larger fixed engagements",
        "diagnostic.html",
        "commercial.html",
    ),
}
PAGES = (KINCELL, LEXINGTON)
ALLOWLIST_PAGES = ("kincell-rtp-qc-release-bridge-lims.html", "lexington-mrf-diversion-gate.html")
CITE = "sledge-kincell-lexington-convert-shelf-20260917-01"
BODY_FOLD_MAX = 2200
NINE_LINK_EXCLUDED = (
    "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
    "https://buy.stripe.com/7sYdR8ckZgHLbCN50K43S0y",
    "https://buy.stripe.com/14AfZg1Gl3UZ7mxfFo43S0x",
    "https://buy.stripe.com/28E9AS70F6378qB2SC43S0w",
)
EXISTING_CONVERT_SHELF_KEYS = (
    "pay.html",
    "commerce.html",
    "payment-capability.html",
    "reply-to-revenue.html",
    "claude-paste.html",
    "mcp-tool-drift.html",
    "failed.html",
    "task-forge.html",
    "subzero-receipt.html",
    "subzero-quote.html",
    "data-license.html",
    "gemini-mcp.html",
    "manual.html",
    "pixel-portfolio.html",
    "todo.html",
    "redundancy.html",
    "distro.html",
    "paperwork-included.html",
    "unbuilt-items.html",
    "webmcp.html",
    "skills.html",
    "swarm.html",
    "embassy.html",
    "glyphs.html",
    "program.html",
    "foldbook.html",
    "flipbook.html",
    "compress.html",
    "command.html",
    "coordination.html",
    "observatory.html",
    "tabletop.html",
    "insights.html",
    "grounding.html",
    "open-door.html",
    "interconnect.html",
    "merge-on-pr.html",
    "landed-work.html",
    "ace-qat-thermal-rheology-capacity-lims.html",
    "agriseed-rush-work-allocator-lims.html",
    "ait-mn-metrc-capacity-gate.html",
    "aquatrace-ops-acceptance.html",
    "aquatrace-work-order-b-production-foundation.html",
    "aquatrace-work-order-c-reporting-offline.html",
    "aquatrace-work-order-f-release-readiness.html",
    "at-grok-adapter-evidence.html",
    "at-grok-cmdp-evidence.html",
    "ats-asphalt-spec-result-lims.html",
    "baddl-eia-accession-release-lims.html",
    "billings-bid-1421-acceptance-runner.html",
    "billings-bid-1421-operations-runner.html",
    "billings-bid-1421-partner-recon.html",
    "bsk-multilab-accession-parity-lims.html",
    "canyon-multisite-regulated-intake.html",
    "ccc-snapshot-toolchain.html",
    "chemtechford-short-hold-intake-lims.html",
    "clark-d4172-proficiency-lims.html",
    "cornell-craft-beverage-intake-lims.html",
    "corrigan-specialty-fuel-blend-dossier-lims.html",
    "csanalytical-expansion-crossline-lims.html",
    "csplabs-express-capacity-assurance-lims.html",
    "ddl-crosssite-method-proficiency-lims.html",
    "discount-concession-leakage.html",
    "eagletrax-split-sample-preflight-lims.html",
    "elevatebio-pittsburgh-replication-lims.html",
    "highpower-ssf-receiving-gate-lims.html",
)
FENCED_PAGES = (
    "flipbook.html",
    "compress.html",
    "program.html",
    "foldbook.html",
    "embassy.html",
    "glyphs.html",
    "command.html",
    "coordination.html",
    "observatory.html",
    "tabletop.html",
    "insights.html",
    "grounding.html",
    "clans.html",
    "discord.html",
    "mirrors.html",
    "net159.html",
    "wakeup.html",
    "memory.html",
    "mirror.html",
    "recents.html",
    "subzero.html",
    "start.html",
    "ledger.html",
    "writing.html",
    "cweather.html",
    "visual.html",
    "titanmcp.html",
    "plug.html",
    "wire.html",
    "open-door.html",
    "interconnect.html",
    "owner-now-revenue.html",
    "paid-opportunities.html",
    "merge-on-pr.html",
    "landed-work.html",
    "demand-survive.html",
    "first-night.html",
    "ace-qat-thermal-rheology-capacity-lims.html",
    "agriseed-rush-work-allocator-lims.html",
    "ait-mn-metrc-capacity-gate.html",
    "aquatrace-ops-acceptance.html",
    "aquatrace-work-order-b-production-foundation.html",
    "aquatrace-work-order-c-reporting-offline.html",
    "aquatrace-work-order-f-release-readiness.html",
    "at-grok-adapter-evidence.html",
    "at-grok-cmdp-evidence.html",
    "ats-asphalt-spec-result-lims.html",
    "baddl-eia-accession-release-lims.html",
    "billings-bid-1421-acceptance-runner.html",
    "billings-bid-1421-operations-runner.html",
    "billings-bid-1421-partner-recon.html",
    "bsk-multilab-accession-parity-lims.html",
    "canyon-multisite-regulated-intake.html",
    "ccc-snapshot-toolchain.html",
    "chemtechford-short-hold-intake-lims.html",
    "clark-d4172-proficiency-lims.html",
    "cornell-craft-beverage-intake-lims.html",
    "corrigan-specialty-fuel-blend-dossier-lims.html",
    "csanalytical-expansion-crossline-lims.html",
    "csplabs-express-capacity-assurance-lims.html",
    "ddl-crosssite-method-proficiency-lims.html",
    "discount-concession-leakage.html",
    "eagletrax-split-sample-preflight-lims.html",
    "elevatebio-pittsburgh-replication-lims.html",
    "highpower-ssf-receiving-gate-lims.html",
)


def _load_host(name: str):
    path = ROOT / "host" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(
        f"sledge_kincell_lexington_{name}", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


payment_capability = _load_host("payment_capability")


def live_buy_urls(html: str) -> set[str]:
    """Exact https://buy.stripe.com/<path> hrefs. Does not reconstruct http://."""
    return set(BUY_HTTPS_URL.findall(html))


def http_buy_duplicate(html: str) -> bool:
    return HTTP_BUY_DUP.search(html) is not None


def convert_shelf(html: str) -> str:
    """First-screen Buy now shelf section, cut at its own close."""
    after = html.split('id="buy-now-live-checkout"', 1)[1]
    return after.split("</section>", 1)[0]


def live_cash_slice(html: str) -> str:
    after = html.split('id="live-cash"', 1)[1]
    if "</section>" in after:
        return after.split("</section>", 1)[0]
    if "</p>" in after:
        return after.split("</p>", 1)[0]
    return after


class TestSledgeKincellLexingtonConvertShelf2026091701(unittest.TestCase):
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
                self.assertEqual(
                    payment_capability.https_buy_checkout_urls(html),
                    ALLOWED_LIVE_BUY_URLS,
                )
                self.assertFalse(http_buy_duplicate(html))
                self.assertFalse(payment_capability.http_buy_duplicate(html))
                self.assertNotIn("http://buy.stripe.com/", html.lower())
                self.assertNotIn("donate.stripe.com", html)
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertIn(url, html)
                    self.assertEqual(html.count(url), 1, url)
                    self.assertEqual(
                        html.count(url.replace("https://", "http://", 1)), 0
                    )
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
                for marker in LIVE_CASH_EXTRA[page.name]:
                    self.assertIn(marker, html, marker)
                body_at = html.lower().find("<body")
                shelf_at = html.find('id="buy-now-live-checkout"')
                live_cash_at = html.find('id="live-cash"')
                self.assertGreater(body_at, -1)
                self.assertGreater(shelf_at, -1)
                self.assertGreater(shelf_at, body_at)
                self.assertGreater(live_cash_at, shelf_at)
                self.assertLess(
                    shelf_at - body_at,
                    BODY_FOLD_MAX,
                    f"{page.name} Buy shelf not first-screen after <body>",
                )
                for url in ALLOWED_LIVE_BUY_URLS:
                    self.assertLess(
                        html.find(url) - body_at,
                        BODY_FOLD_MAX,
                        f"{page.name} {url} not first-screen after <body>",
                    )
                for label in BUY_LABELS:
                    self.assertLess(
                        html.find(label) - body_at,
                        BODY_FOLD_MAX,
                        f"{page.name} {label} not first-screen after <body>",
                    )
                self.assertIsNone(re.search(r"\blogin\b", shelf, flags=re.I))
                self.assertNotIn("live Stripe URLs", html)
                self.assertNotIn(">Pay ", html)
                self.assertIn(".cta{", html)
                self.assertNotIn("titanmcp", shelf.lower())

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
        self.assertIn("HTTPS-exact", text)
        for url in ALLOWED_LIVE_BUY_URLS:
            self.assertIn(url, text)
        self.assertNotIn("https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b", text)
        for name in (
            "kincell-rtp-qc-release-bridge-lims.html",
            "lexington-mrf-diversion-gate.html",
            "commercial.html",
            "diagnostic.html",
        ):
            self.assertTrue((ROOT / name).is_file(), name)
            self.assertIn(name, text)
        self.assertNotIn("index.html", text)

    def test_payment_capability_enrolls_https_exact_and_rejects_http_duplicate(
        self,
    ) -> None:
        http_error = "convert shelf must not duplicate live buys over http://"
        reuse_error = (
            "convert shelf must reuse exactly the existing live buy.stripe.com URLs"
        )
        for name in EXISTING_CONVERT_SHELF_KEYS:
            self.assertIn(name, payment_capability.CONVERT_SHELF_LIVE_BUYS)
            self.assertIn(name, payment_capability.PUBLIC_HTML)
        for name in ALLOWLIST_PAGES:
            allowed = payment_capability.CONVERT_SHELF_LIVE_BUYS[name]
            self.assertEqual(allowed, ALLOWED_LIVE_BUY_URLS)
            self.assertIs(
                allowed, payment_capability.PEERS_REPLY_CONVERT_SHELF_LIVE_BUYS
            )
            self.assertIn(name, payment_capability.PUBLIC_HTML)
            page_html = (ROOT / name).read_text(encoding="utf-8")
            self.assertEqual(
                payment_capability.html_stripe_url_errors(name, page_html),
                [],
            )
            self.assertEqual(
                live_buy_urls(page_html),
                ALLOWED_LIVE_BUY_URLS,
            )
            forged = page_html.replace(
                "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
                "https://buy.stripe.com/not-a-canonical-link",
                1,
            )
            self.assertEqual(
                payment_capability.html_stripe_url_errors(name, forged),
                ["%s %s" % (name, reuse_error)],
            )
            poisoned = (
                page_html
                + '<a href="http://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07">dup</a>'
            )
            self.assertEqual(live_buy_urls(poisoned), ALLOWED_LIVE_BUY_URLS)
            self.assertEqual(
                payment_capability.https_buy_checkout_urls(poisoned),
                ALLOWED_LIVE_BUY_URLS,
            )
            self.assertTrue(http_buy_duplicate(poisoned))
            self.assertTrue(payment_capability.http_buy_duplicate(poisoned))
            self.assertEqual(
                payment_capability.html_stripe_url_errors(name, poisoned),
                ["%s %s" % (name, http_error)],
            )
            http_only = page_html.replace(
                "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
                HTTP_DUP_HREF,
                1,
            )
            self.assertNotEqual(live_buy_urls(http_only), ALLOWED_LIVE_BUY_URLS)
            self.assertTrue(payment_capability.http_buy_duplicate(http_only))
            self.assertEqual(
                payment_capability.html_stripe_url_errors(name, http_only),
                ["%s %s" % (name, reuse_error)],
            )


if __name__ == "__main__":
    unittest.main()
