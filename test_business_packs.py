#!/usr/bin/env python3
"""Contracts for the thin Business Packs factory scaffold."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
SKU = ROOT / "land" / "sku-business-packs-20260902.md"
TEMPLATE = ROOT / "land" / "business-pack-template-20260902.md"
CATALOG = ROOT / "revenue" / "outcome_commerce" / "business_packs_catalog.json"
POST = ROOT / "p" / "goat-business-packs-ready-20260902-01.md"
SLOT = ROOT / "packs" / "_template"
REQUIRED_SLOT = ("instructions.md", "assets.md", "offer.md", "week1.md")
EXTRA_SLOT = ("checkout.md", "keep-vs-sell.md", "README.md")
INDEXED_ADDITIVE = ("creative_brief.md", "rating.md", "waitlist-slot.md")
SCAFFOLD_PATHS = (
    SKU,
    TEMPLATE,
    CATALOG,
    POST,
    ROOT / "packs" / "README.md",
    SLOT / "README.md",
    SLOT / "instructions.md",
    SLOT / "assets.md",
    SLOT / "offer.md",
    SLOT / "week1.md",
    SLOT / "checkout.md",
    SLOT / "keep-vs-sell.md",
)
TIERS = ("$20", "$100", "$200", "$1000", "$10k")
FAKE_CHECKOUT_URL = (
    "https://buy.stripe.com/",
    "https://donate.stripe.com/",
)
INTACT = (
    ROOT / "chunks",
    ROOT / "muhl" / "docs",
    ROOT / "pay.html",
    ROOT / "commerce.html",
    ROOT / "land" / "stripe-payment-links-20260826.md",
    ROOT / "revenue" / "outcome_commerce" / "catalog.json",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class BusinessPacksScaffoldTests(unittest.TestCase):
    def test_required_files_exist(self):
        for path in SCAFFOLD_PATHS:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertTrue(path.is_file(), path)

    def test_empty_slot_lists_required_files(self):
        readme = _read(SLOT / "README.md")
        for name in REQUIRED_SLOT:
            self.assertIn(name, readme)
            self.assertTrue((SLOT / name).is_file())
        for name in EXTRA_SLOT:
            self.assertTrue((SLOT / name).is_file())
        for name in INDEXED_ADDITIVE:
            self.assertIn(name, readme)
            self.assertTrue((SLOT / name).is_file(), name)
        self.assertNotIn("337 NO", readme)
        self.assertIn("OWNER_UNSET", readme)
        self.assertIn("marketing=owner", readme)

    def test_price_tiers_and_factory_loop(self):
        sku = _read(SKU)
        template = _read(TEMPLATE)
        post = _read(POST)
        catalog = json.loads(_read(CATALOG))
        for blob in (sku, template, post):
            for tier in TIERS:
                self.assertIn(tier, blob)
            self.assertIn("generate", blob)
            self.assertIn("KEEP", blob)
            self.assertIn("SELL", blob)
            self.assertIn("owner pastes live payment link", blob.lower())
        amounts = [row["usd"] for row in catalog["tiers"]]
        self.assertEqual(amounts, ["20", "100", "200", "1000", "10000"])
        self.assertEqual(
            catalog["factory_loop"],
            ["generate", "measure revenue signal", "KEEP", "SELL"],
        )

    def test_marketing_is_owner_owned(self):
        for path in (SKU, TEMPLATE, POST, CATALOG):
            text = _read(path).lower()
            self.assertIn("owner-owned", text)
            self.assertNotIn("ads.google.com", text)
            self.assertNotIn("facebook.com/ads", text)
        sku = _read(SKU)
        self.assertIn("Marketing is owner-owned", sku)
        self.assertIn("Do not add ad copy campaigns", sku)
        self.assertIn("or a marketing agent", sku)

    def test_open_door_and_no_auth_language(self):
        sku = _read(SKU)
        post = _read(POST)
        for blob in (sku, post):
            self.assertIn("Open door", blob)
            self.assertIn("Possessing the", blob)
            self.assertNotRegex(blob, r"\blogin wall\b")
        self.assertIn("No login", sku)
        catalog = json.loads(_read(CATALOG))
        self.assertTrue(catalog["open_door"])
        self.assertEqual(catalog["auth"], "none")

    def test_no_invented_stripe_urls_in_scaffold(self):
        for path in SCAFFOLD_PATHS:
            text = _read(path)
            for marker in FAKE_CHECKOUT_URL:
                with self.subTest(path=str(path.relative_to(ROOT)), marker=marker):
                    self.assertNotIn(marker, text)
            self.assertNotRegex(text, r"plink_[A-Za-z0-9]+")
        checkout = _read(SLOT / "checkout.md")
        self.assertIn("Owner pastes live Payment Link", checkout)
        self.assertIn("NOT_MINTED", checkout)

    def test_post_exact_id_and_goat_claim(self):
        text = _read(POST)
        self.assertIn("id: goat-business-packs-ready-20260902-01", text)
        self.assertIn("from: GOAT", text)
        self.assertIn("Claim GOAT", text)
        self.assertNotIn("supersedes:", text)

    def test_does_not_replace_fat_catalog_or_live_skus(self):
        catalog = json.loads(_read(CATALOG))
        self.assertEqual(catalog["kind"], "BUSINESS_PACKS_FACTORY_CATALOG")
        self.assertEqual(catalog["listings"], [])
        self.assertIn("Does not replace revenue/outcome_commerce/catalog.json", catalog["note"])
        sku = _read(SKU)
        self.assertIn("Do not remint sku-tip-20260826", sku)
        self.assertIn("cursor-slack-business-packs-channel-20260902-01", sku)
        for path in INTACT:
            self.assertTrue(path.exists(), path)

    def test_no_mno_actuation(self):
        sku = _read(SKU)
        self.assertIn("Do not smash commons.mno", sku)
        self.assertIn("337 NO", sku)
        self.assertNotIn("fire_337=true", sku)

    def test_unique_pack_law(self):
        sku = _read(SKU)
        template = _read(TEMPLATE)
        post = _read(POST)
        catalog = json.loads(_read(CATALOG))
        for path, blob in ((SKU, sku), (TEMPLATE, template), (POST, post)):
            with self.subTest(path=str(path.relative_to(ROOT))):
                lower = blob.lower()
                self.assertIn("fresh package", lower)
                self.assertIn("do not sell the same business repeatedly", lower)
                self.assertIn("brand", lower)
                self.assertIn("domain", lower)
                self.assertIn("checkout", lower)
                self.assertIn("assets", lower)
                self.assertIn("instructions", lower)
                self.assertIn("clone", lower)
                self.assertIn("cursor-business-packs-unique-20260902-01", blob)
                self.assertIn("do not describe multi-copy identical inventory", lower)
        self.assertIn("Marketing may stand on uniqueness only when", sku)
        self.assertIn("Marketing may stand on uniqueness only when", template)
        self.assertIn("Marketing may stand on uniqueness only when", post)
        law = catalog["unique_pack_law"]
        self.assertEqual(law["each_purchase"], "fresh_package")
        self.assertIs(law["clone_stamp_inventory"], False)
        self.assertEqual(
            law["instance_fields"],
            ["brand", "domain", "checkout", "assets", "instructions"],
        )
        self.assertEqual(law["receipt"], "p/cursor-business-packs-unique-20260902-01.md")
        self.assertEqual(law["card"], "ground/BUSINESS_PACKS.md")
        self.assertIn("fresh package", _read(SLOT / "offer.md").lower())
        self.assertIn("fresh package", _read(SLOT / "keep-vs-sell.md").lower())
        self.assertIn("may be similar", sku.lower())
        self.assertIn("must not", sku.lower())
        self.assertIn("copy-paste", sku.lower())
        self.assertIn("may be similar", template.lower())
        self.assertIn("copy-paste", template.lower())
        self.assertIn("may be similar", post.lower())
        self.assertIn("copy-paste", post.lower())

    def test_mystery_box_nuts_not_lottery(self):
        sku = _read(SKU)
        template = _read(TEMPLATE)
        post = _read(POST)
        catalog = json.loads(_read(CATALOG))
        for path, blob in ((SKU, sku), (TEMPLATE, template), (POST, post)):
            with self.subTest(path=str(path.relative_to(ROOT))):
                lower = blob.lower()
                self.assertIn("mystery box", lower)
                self.assertIn("the nuts", lower)
                self.assertIn("not a lottery", lower)
                self.assertIn("not gambling", lower)
                self.assertIn("tokenjunkielabs", lower.replace(" ", ""))
                self.assertIn("tjlabs", lower.replace(" ", ""))
                self.assertIn("value range", lower)
                self.assertNotRegex(lower, r"\b\d+(\.\d+)?\s*%\s*(odds|chance|probability)\b")
                self.assertNotRegex(lower, r"\b(odds|chance)\s*(of|=|:)\s*\d")
        box = catalog["mystery_box"]
        self.assertTrue(box["not_a_lottery"])
        self.assertTrue(box["not_gambling"])
        self.assertEqual(box["odds"], "UNMEASURED")
        self.assertEqual(box["marketing"], "owner-owned")
        self.assertIn("do not invent odds percentages", box["odds_rule"])
        self.assertIn("TokenJunkieLabs", box["frame"])
        self.assertIn("still owner-owned", sku.lower())
        self.assertIn("still owner-owned", template.lower())
        self.assertIn("still owner-owned", post.lower())


if __name__ == "__main__":
    unittest.main()
