#!/usr/bin/env python3
"""Muhlnickel FREE SAMPLE page stays an open door and does not invent cash."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "muhlnickel-free-sample.html"
PACK = ROOT / "revenue" / "muhlnickel_free_sample" / "sales_pack.json"
SEED0 = ROOT / "muhl" / "containers" / "MUHLNICKEL_DISTRO" / "SEED0.mno"
RESOURCES = ROOT / "resources.html"
COMMERCE = ROOT / "commerce.html"
ATTESTED = ROOT / "attested-inference.html"
PITCH = ROOT / "revenue" / "muhlnickel_inference" / "pitch_pack.json"
SEED0_BLOB = "59734967a743d56d855cf39f3968c6b8c42cba60"

class StrictHTMLParser(HTMLParser):
    pass


class MuhlnickelFreeSampleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page = PAGE.read_text(encoding="utf-8")
        self.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_page_is_public_html_and_parses(self) -> None:
        self.assertTrue(PAGE.is_file())
        parser = StrictHTMLParser()
        parser.feed(self.page)
        parser.close()
        self.assertIn("<!DOCTYPE html>", self.page)
        self.assertIn("PUBLIC OPEN DOOR", self.page)
        self.assertIn("No login", self.page)
        self.assertIn("Possessing this link is authorization", self.page)

    def test_page_has_no_admission_or_auth_gates(self) -> None:
        lowered = self.page.lower()
        self.assertIn("public open door", lowered)
        self.assertIn("no login", lowered)
        self.assertIn("possessing this link is authorization", lowered)
        self.assertNotRegex(self.page, r"<form[^>]*>")
        self.assertNotIn('type="password"', self.page)
        self.assertNotIn("oauth", lowered)
        self.assertNotIn("bearer token", lowered)
        self.assertNotIn("required credential", lowered)

    def test_page_shows_real_public_seed_sample(self) -> None:
        seed = SEED0.read_bytes()
        self.assertEqual(len(seed), 8192)
        self.assertTrue(seed.startswith(b"MUHLPKG1"))
        blob = subprocess.check_output(
            ["git", "hash-object", str(SEED0)],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(blob, SEED0_BLOB)
        self.assertIn("SEED0.mno", self.page)
        self.assertIn("muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno", self.page)
        self.assertIn("8192", self.page)
        self.assertIn("MUHLPKG1", self.page)
        self.assertIn(SEED0_BLOB, self.page)
        self.assertIn("3 + 5 → 8", self.page)
        self.assertIn("test_published_computers_in_repo", self.page)
        self.assertIn("Click SEED0.mno, then read the already-landed 3+5→8 receipt", self.page)

    def test_page_is_honest_and_invents_no_payment_or_cash(self) -> None:
        lowered = self.page.lower()
        self.assertIn("not a live 70b", lowered)
        self.assertIn("cash usd 0", lowered)
        self.assertIn("not a new stripe or shopify url", lowered)
        self.assertNotIn("buy.stripe.com", lowered)
        self.assertNotIn("checkout.stripe.com", lowered)
        self.assertNotIn("myshopify.com", lowered)
        self.assertNotIn("payment received", lowered)
        self.assertNotIn("customer paid", lowered)
        self.assertNotIn("cash collected", lowered)
        self.assertNotRegex(self.page, r"mailto:[^\"']+")

    def test_sales_pack_is_pasteable_and_cashless(self) -> None:
        self.assertEqual(self.pack["id"], "muhlnickel-free-sample-20260830-01")
        self.assertEqual(self.pack["kind"], "FREE_SAMPLE_SALES_PACK")
        self.assertIn("muhlnickel-free-sample.html", self.pack["canonical_page"])
        self.assertIn(SEED0_BLOB, self.pack["one_sentence"])
        self.assertIn(SEED0_BLOB, self.pack["commons_blurb"])
        self.assertIn(self.pack["commons_blurb"].split("\n")[0], self.page)
        self.assertEqual(self.pack["truth"]["cash_usd"], 0)
        self.assertFalse(self.pack["truth"]["buyer_contacted"])
        self.assertFalse(self.pack["truth"]["live_70b_inference"])
        self.assertIsNone(self.pack["truth"]["new_stripe_url"])
        self.assertIsNone(self.pack["truth"]["new_shopify_url"])
        self.assertEqual(self.pack["proof"]["git_blob"], SEED0_BLOB)
        self.assertEqual(self.pack["proof"]["bytes"], 8192)

    def test_house_style_links_do_not_remint_paid_contracts(self) -> None:
        resources = RESOURCES.read_text(encoding="utf-8")
        commerce = COMMERCE.read_text(encoding="utf-8")
        attested = ATTESTED.read_text(encoding="utf-8")
        pitch = PITCH.read_text(encoding="utf-8")
        self.assertIn('href="./muhlnickel-free-sample.html"', resources)
        self.assertIn('href="./muhlnickel-free-sample.html"', commerce)
        self.assertIn("10 million generated tokens for $1", attested)
        self.assertIn("$500", attested)
        self.assertIn("$1,500", attested)
        self.assertIn("$2,500", attested)
        self.assertIn("PRODUCT_RANGE_OUTREACH_PACK", pitch)
        self.assertNotIn("sales-free-sample-pack-20260830-01.md", self.page)


if __name__ == "__main__":
    unittest.main()
