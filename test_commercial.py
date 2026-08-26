#!/usr/bin/env python3
"""Contract checks for the canonical White Box commercial offer and open door."""
from __future__ import annotations

import json
import os
import re
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))


def read(path: str) -> str:
    with open(os.path.join(HERE, path), encoding="utf-8") as handle:
        return handle.read()


class CommercialOfferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads(read("commercial.json"))
        cls.html = read("commercial.html")

    def test_canonical_offer_and_exact_price(self) -> None:
        self.assertEqual(self.catalog["kind"], "COMMERCIAL_OFFER")
        self.assertEqual(self.catalog["canonical_source"], "commercial.json")
        offer = self.catalog["offer"]
        self.assertEqual(offer["offer_id"], "white-box-gguf-pilot-30d")
        self.assertEqual(offer["public_product_name"], "White Box")
        self.assertEqual(offer["target"], "one customer-owned GGUF model family")
        self.assertEqual(offer["term_calendar_days"], 30)
        self.assertEqual(offer["fee"]["currency"], "USD")
        self.assertEqual(offer["fee"]["fixed_amount"], 30_000)
        milestones = offer["fee"]["milestones"]
        self.assertEqual([row["amount"] for row in milestones], [15_000, 15_000])
        self.assertEqual(sum(row["amount"] for row in milestones), 30_000)
        self.assertEqual(milestones[0]["due"], "on NDA and SOW signing")
        self.assertEqual(milestones[1]["due"], "on delivery of the agreed pilot package")

    def test_follow_on_and_product_boundary(self) -> None:
        offer = self.catalog["offer"]
        follow = offer["follow_on"]
        self.assertEqual(follow["term_months"], 12)
        self.assertEqual(follow["currency"], "USD")
        self.assertEqual((follow["amount_from"], follow["amount_to"]), (100_000, 175_000))
        self.assertTrue(follow["separately_scoped"])
        boundary = offer["commercial_boundary"]
        self.assertFalse(boundary["computer_is_the_product"])
        self.assertFalse(boundary["computer_or_factory_transfer"])
        self.assertIn("the foundry and reproduction methods", boundary["provider_keeps"])

    def test_values_are_grounded_in_established_pack(self) -> None:
        fee = read("muhl/lda-docs/muhl_revenue_add_20260813/FEE.md")
        sow = read("muhl/lda-docs/muhl_revenue_add_20260813/SOW_OUTLINE.md")
        law = read("muhl/lda-docs/muhl_revenue_add_20260813/PRODUCT_LAW.md")
        for exact in (
            "$30,000 fixed",
            "30-day White Box NDA pilot",
            "$15,000 on NDA and SOW signing",
            "$15,000 on delivery of the agreed pilot package",
            "12-month organization license from $100,000 to $175,000",
        ):
            self.assertIn(exact, fee)
        self.assertIn("**Term:** 30 calendar days", sow)
        self.assertIn("The computer is not the product", law)
        self.assertIn("White Box on **their** GGUF", law)
        for source in self.catalog["source_docs"]:
            self.assertTrue(os.path.isfile(os.path.join(HERE, source["path"])), source["path"])

    def test_public_interest_is_non_confidential_and_not_payment(self) -> None:
        interest = self.catalog["public_interest"]
        self.assertEqual(interest["visibility"], "PUBLIC")
        self.assertEqual(interest["confidentiality"], "NON_CONFIDENTIAL_ONLY")
        self.assertEqual(interest["route"]["to"], "OFFER")
        self.assertEqual(
            self.catalog["offer"]["fee"]["payment_collection"],
            "NOT_PROVIDED_ON_THIS_PAGE",
        )
        blocked = " ".join(interest["never_include"]).lower()
        self.assertIn("model files", blocked)
        self.assertIn("datasets", blocked)
        self.assertIn("credentials", blocked)

    def test_html_reads_canonical_json_and_uses_open_carrier(self) -> None:
        html = self.html
        self.assertIn('fetch("./commercial.json?v="', html)
        self.assertIn('canonical_source !== "commercial.json"', html)
        self.assertIn('<form id="say">', html)
        self.assertRegex(html, r'<input type="hidden" name="to" value="OFFER">')
        self.assertIn('name="subject" value="WHITE BOX COMMERCIAL INTEREST"', html)
        self.assertIn('<script src="./carrier.js?v=20260824a"></script>', html)
        self.assertIn("PUBLIC OPEN DOOR", html)
        self.assertIn("No login", html)
        self.assertIn("public and non-confidential", html)
        self.assertIn("does not collect payment or upload model files", html)
        self.assertNotRegex(html, r'<input\b[^>]*type=["\']file["\']')
        self.assertIn(
            '<span id="compose-attach" hidden aria-hidden="true" '
            'data-commercial-no-upload="true"></span>',
            html,
        )
        self.assertIn(
            'if (form.querySelector("#compose-attach")) return;',
            read("session.js"),
        )
        from_field = re.search(r'<input name="from"[^>]*>', html)
        self.assertIsNotNone(from_field)
        self.assertNotIn("required", from_field.group(0))

    def test_exact_offer_is_visible_without_javascript(self) -> None:
        for exact in (
            "$30,000 fixed · 30 calendar days · one customer-owned GGUF model family",
            "$15,000 on NDA and SOW signing",
            "$15,000 on delivery of the agreed pilot package",
            "$100,000 to $175,000",
            "$2,500 same-day proof",
            "$15,000 five-day recovery",
            "tokenjunkielabs@gmail.com",
        ):
            self.assertIn(exact, self.html)

    def test_agent_index_carries_the_same_ladder(self) -> None:
        source = read("llms_txt.py")
        baked = read("llms.txt")
        for exact in (
            "## Commercial",
            "$2,500 same-day crash-resume proof",
            "$15,000 five-day recovery sprint",
            "$12,000 GGUF diagnostic",
            "$30,000 White Box pilot",
            "$45,000 Muhlnickel / Titan keep-or-build",
            "tokenjunkielabs@gmail.com",
            "All SKUs remain sellable",
        ):
            self.assertIn(exact, source)
            self.assertIn(exact, baked)


if __name__ == "__main__":
    unittest.main()
