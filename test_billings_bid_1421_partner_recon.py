#!/usr/bin/env python3
"""Binary test for Bid 1421 research-only partner recon."""
from __future__ import annotations

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
RECEIPT = ROOT / "p" / "billings-bid-1421-partner-recon-20260831-01.md"
PAGE = ROOT / "billings-bid-1421-partner-recon.html"
JSON_PATH = ROOT / "revenue" / "billings_bid_1421" / "partner_recon" / "partners.json"
FIXTURE_DIR = ROOT / "revenue" / "billings_bid_1421" / "instrument_fixtures"
EMAIL_KEYS = {
    "email",
    "emails",
    "guessed_email",
    "guessed_emails",
    "contact_email",
    "sales_email",
    "scraped_email",
}
OWNER_PHONE = "6803283352"
CITY_EMAIL = "armstrongc@billingsmt.gov"
STOLEN = (
    ROOT / "p" / "dealer-service-lead-rescue-20260831-01.md",
    ROOT / "p" / "billings-bid-1421-instrument-fixtures-20260831-01.md",
)


def _walk_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_keys(item)


class BillingsBid1421PartnerReconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = RECEIPT.read_text(encoding="utf-8")
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        cls.partners = cls.data["partners"]

    def test_receipt_exists(self):
        self.assertTrue(RECEIPT.is_file(), RECEIPT.name)
        self.assertIn("id: billings-bid-1421-partner-recon-20260831-01", self.receipt)
        self.assertIn("RESEARCH_ONLY", self.receipt)
        self.assertIn("NO_CONTACT", self.receipt)
        self.assertIn("NO_PARTNERSHIP_CLAIMED", self.receipt)
        self.assertIn("cash_usd: 0", self.receipt)

    def test_surfaces_exist(self):
        self.assertTrue(PAGE.is_file(), PAGE.name)
        self.assertTrue(JSON_PATH.is_file(), JSON_PATH.name)
        self.assertEqual(self.data["id"], "billings-bid-1421-partner-recon-20260831-01")
        self.assertEqual(self.data["kind"], "research_only_partner_recon")
        self.assertEqual(self.data["cash_usd"], 0)
        self.assertTrue(self.data["no_contact"])
        self.assertTrue(self.data["no_partnership_claimed"])

    def test_every_partner_row_has_source_url(self):
        self.assertGreaterEqual(len(self.partners), 4)
        self.assertLessEqual(len(self.partners), 8)
        for row in self.partners:
            with self.subTest(row["legal_name"]):
                self.assertTrue(row["capability_url"].startswith("https://"), row)
                self.assertTrue(row["public_contact_route"]["url"].startswith("https://"), row)
                self.assertTrue(row["source_urls"], row)
                for url in row["source_urls"]:
                    self.assertTrue(url.startswith("https://"), url)
                self.assertIn(row["capability_url"], self.receipt)
                self.assertIn(row["legal_name"], self.receipt)
                page_plain = self.page.replace("&amp;", "&")
                self.assertIn(row["legal_name"], page_plain)
                self.assertIn(row["capability_url"], self.page)

    def test_no_guessed_email_fields(self):
        keys = set(_walk_keys(self.data))
        self.assertEqual(keys & EMAIL_KEYS, set())
        dumped = json.dumps(self.data)
        self.assertNotRegex(dumped, r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        self.assertNotIn(CITY_EMAIL, self.receipt)
        self.assertNotIn(CITY_EMAIL, self.page)
        self.assertNotIn(CITY_EMAIL, dumped)
        self.assertNotRegex(self.receipt, r"(?i)guessed[_-]email\s*[:=]")
        self.assertNotRegex(self.page, r"(?i)guessed[_-]email\s*[:=]")

    def test_cannot_claim_rows_are_labeled(self):
        statuses = {row["legal_name"]: row["row_status"] for row in self.partners}
        self.assertIn("CANNOT_CLAIM", statuses.values())
        self.assertIn("EVIDENCE_NOW", statuses.values())
        for row in self.partners:
            self.assertIn(row["row_status"], ("EVIDENCE_NOW", "CANNOT_CLAIM"))
            self.assertIn(row["teaming"], ("PLAUSIBLE", "UNKNOWN"))
            if row["row_status"] == "CANNOT_CLAIM":
                self.assertIn("CANNOT_CLAIM", row["instrument_software_fit"] + row["teaming_note"])
                self.assertIn(row["legal_name"], self.receipt)
                self.assertIn("CANNOT_CLAIM", self.receipt)
                pattern = re.compile(
                    re.escape(row["legal_name"].replace("&", "&amp;")) + r".{0,240}CANNOT_CLAIM",
                    re.S,
                )
                self.assertRegex(self.page, pattern)
        self.assertEqual(statuses["Microsoft Corporation"], "CANNOT_CLAIM")
        self.assertIn("cannot_claim", self.data)
        self.assertTrue(self.data["cannot_claim"])
        self.assertTrue(any(row["row_status"] == "CANNOT_CLAIM" for row in self.partners))

    def test_page_is_research_not_a_bid(self):
        self.assertIn("RESEARCH_ONLY", self.page)
        self.assertIn("NO_CONTACT", self.page)
        self.assertIn("not a bid", self.page.lower())
        self.assertIn("not a sales page", self.page.lower())
        self.assertNotIn("login", self.page.lower().split("authorization")[0] + "authorization")
        self.assertNotIn("MEMORY_GATE", self.page)
        self.assertIn("DO-NOT-CONTACT", self.page)
        self.assertIn("(406) 698-1060", self.page)
        self.assertNotIn(OWNER_PHONE, self.page)
        self.assertNotIn(OWNER_PHONE, self.receipt)
        self.assertNotIn(OWNER_PHONE, json.dumps(self.data))

    def test_public_references_are_vendor_named_or_none(self):
        refs = self.data["public_references"]
        self.assertTrue(refs)
        for ref in refs:
            self.assertFalse(ref["ours"])
            self.assertTrue(ref["url"].startswith("https://"))
            self.assertIn(ref["customer"], self.page)
            self.assertIn(ref["customer"], self.receipt)
        self.assertIn("None found", self.page)
        self.assertIn("No AquaTrace production deployment found", self.receipt)

    def test_did_not_touch_fixtures_or_steal_lanes(self):
        self.assertTrue(FIXTURE_DIR.is_dir())
        self.assertEqual(self.data["fixture_input"]["touched"], False)
        self.assertIn("592d8b5bc", self.receipt)
        self.assertIn("6674", self.receipt)
        for path in STOLEN:
            self.assertTrue(path.is_file(), path.name)
        self.assertNotEqual(
            (ROOT / "p" / "billings-bid-1421-instrument-fixtures-20260831-01.md").read_text(
                encoding="utf-8"
            ),
            self.receipt,
        )


if __name__ == "__main__":
    unittest.main()
