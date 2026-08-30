#!/usr/bin/env python3
"""Exact-source tests for the public Commons data licensing door."""

import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parent


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class DataLicenseDoorTests(unittest.TestCase):
    def test_archive_inventory_and_readiness_are_exact(self):
        inventory = load_json("revenue/ip/whitebox_archive_inventory.json")
        archive = inventory["archive"]
        self.assertEqual(archive["public_label"], "White Box Research Archive")
        self.assertEqual(archive["file_count"], 7946)
        self.assertEqual(archive["directory_count"], 56)
        self.assertEqual(archive["total_bytes"], 16172446060)
        self.assertEqual(archive["tree_sha256"], "d67234a1e0d69dba621f4073ecfbaf77db298134d3bd516fba30fc2062467bc9")
        readiness = inventory["commercial_readiness"]
        self.assertFalse(readiness["archive_license_offer_ready"])
        self.assertFalse(readiness["pricing_ready"])

        probe = load_json("revenue/ip/whitebox_archive_license_probe.json")
        self.assertEqual(probe["summary"]["located_models"], 8)
        self.assertFalse(probe["commercial_readiness"]["transfer_cleared"])

    def test_ci_corpus_stays_license_blocked(self):
        corpus = load_json("revenue/data/ci_receipt_corpus.json")
        self.assertEqual(corpus["source_pool"]["json_files_seen"], 50)
        self.assertEqual(corpus["scan"]["files_scanned"], 9)
        self.assertEqual(corpus["scan"]["bytes_scanned"], 3733)
        self.assertTrue(all(count == 0 for count in corpus["scan"]["hit_counts"].values()))
        self.assertEqual(corpus["license"]["status"], "NOASSERTION")
        self.assertEqual(corpus["release"]["state"], "BLOCKED_LICENSE_REQUIRED")
        self.assertFalse(corpus["release"]["transfer_ready"])
        self.assertFalse(corpus["truth"]["buyer_interest_verified"])
        self.assertFalse(corpus["truth"]["cash_received"])

    def test_service_prices_and_archive_boundary_match_source(self):
        offers = {row["id"]: row for row in load_json("revenue/ip/whitebox_collaboration_offers.json")["offers"]}
        archive = offers["whitebox-archive-license"]
        self.assertEqual(archive["state"], "BLOCKED_EVIDENCE_REQUIRED")
        self.assertFalse(archive["price"]["known"])
        self.assertFalse(archive["uses_owner_archive_payload"])
        self.assertFalse(archive["transfer_payload"])
        benchmark = offers["whitebox-sponsored-benchmark"]
        self.assertEqual(benchmark["price"]["amount_usd"], 12000)
        self.assertEqual(benchmark["duration_days"], 10)
        evaluation = offers["whitebox-private-evaluation"]
        self.assertEqual(evaluation["price"]["amount_usd"], 30000)
        self.assertEqual(evaluation["duration_days"], 30)

    def test_page_is_an_open_truthful_inquiry_door(self):
        page = (ROOT / "data-license.html").read_text(encoding="utf-8")
        self.assertIn('name="to" value="OFFER"', page)
        self.assertIn('name="board" value="OFFER"', page)
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        asset_v = re.search(r'^ASSET_V\s*=\s*"([^"]+)"', hub, re.M).group(1)
        self.assertIn('src="./carrier.js?v=%s"' % asset_v, page)
        self.assertIn("opportunity signal, not a valuation, buyer, agreement, or sale", page)
        self.assertIn("BLOCKED_LICENSE_REQUIRED", page)
        self.assertIn("EVIDENCE REVIEW REQUIRED", page)
        self.assertNotIn("$2.5M", page)
        self.assertNotIn("transfer ready", page.lower())
        self.assertNotIn("login required", page.lower())
        for field in (
            "PUBLIC_USE_CASE:", "DATA_FAMILY:", "FIELDS_OR_SIGNALS_NEEDED:",
            "TIME_RANGE:", "LICENSE_OR_EXCLUSIVITY:", "DELIVERY_FORMAT:",
            "PUBLIC_CONTACT_URL:",
        ):
            self.assertIn(field, page)

    def test_commerce_links_the_data_door(self):
        commerce = (ROOT / "commerce.html").read_text(encoding="utf-8")
        self.assertIn('<a href="./data-license.html">data licensing</a>', commerce)


if __name__ == "__main__":
    unittest.main()
