#!/usr/bin/env python3
"""Unique-pack law: each customer purchase is a fresh package. Not a Commons gate."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_unique as unique  # noqa: E402


class BusinessPackUniqueTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = unique.load_law()
        self.card = (ROOT / "ground" / "BUSINESS_PACKS.md").read_text(encoding="utf-8")
        self.door = (ROOT / "business-packs.html").read_text(encoding="utf-8")

    def test_law_is_not_a_commons_gate(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertEqual(self.law["source_channel_id"], "C0BU7JAPUH3")
        self.assertEqual(self.law["source_slack_ts"], "1788323099.458239")
        self.assertEqual(self.law["marketing"], "bryce_only")
        self.assertIs(self.law["agents_spend_ads"], False)
        self.assertIs(self.law["no_fake_stripe_urls"], True)
        self.assertIs(self.law["clone_stamp"], False)
        self.assertEqual(self.law["each_purchase"], "fresh_package")
        self.assertEqual(self.law["scaffold_owned_by"], "GOAT")
        self.assertNotIn("337 NO", json.dumps(self.law))
        self.assertNotIn("337 NO", self.card)

    def test_two_sales_same_assets_and_ops_are_clone_stamp(self) -> None:
        sales = [
            {
                "sale_id": "sale-a",
                "assets_sha256": "aa" * 32,
                "ops_sha256": "bb" * 32,
            },
            {
                "sale_id": "sale-b",
                "assets_sha256": "aa" * 32,
                "ops_sha256": "bb" * 32,
            },
        ]
        result = unique.classify_sales(sales)
        self.assertIs(result["gate"], False)
        self.assertTrue(result["clone_stamp"])
        verdicts = {row["sale_id"]: row["verdict"] for row in result["sales"]}
        self.assertEqual(verdicts["sale-a"], "CLONE_STAMP")
        self.assertEqual(verdicts["sale-b"], "CLONE_STAMP")
        self.assertFalse(unique.marketing_uniqueness_ok(sales[0], sales))

    def test_two_sales_distinct_assets_ops_are_unique(self) -> None:
        sales = [
            {
                "sale_id": "sale-a",
                "assets_sha256": "aa" * 32,
                "ops_sha256": "bb" * 32,
            },
            {
                "sale_id": "sale-b",
                "assets_sha256": "cc" * 32,
                "ops_sha256": "dd" * 32,
            },
        ]
        result = unique.classify_sales(sales)
        self.assertFalse(result["clone_stamp"])
        self.assertEqual(result["unique_count"], 2)
        self.assertTrue(unique.marketing_uniqueness_ok(sales[0], sales))
        self.assertTrue(result["no_fake_stripe_urls"])
        self.assertEqual(result["marketing"], "bryce_only")

    def test_same_sale_id_different_fingerprints_is_conflict(self) -> None:
        sales = [
            {
                "sale_id": "sale-a",
                "assets_sha256": "aa" * 32,
                "ops_sha256": "bb" * 32,
            },
            {
                "sale_id": "sale-a",
                "assets_sha256": "cc" * 32,
                "ops_sha256": "dd" * 32,
            },
        ]
        result = unique.classify_sales(sales)
        self.assertIn("sale-a", result["conflicts"])
        row = next(r for r in result["sales"] if r["sale_id"] == "sale-a")
        self.assertEqual(row["verdict"], "CONFLICT")

    def test_missing_assets_or_ops_is_missing_fingerprint(self) -> None:
        result = unique.classify_sales([{"sale_id": "sale-a", "assets_sha256": "aa" * 32}])
        self.assertEqual(result["missing_fingerprint"], ["sale-a"])
        self.assertEqual(result["sales"][0]["verdict"], "MISSING_FINGERPRINT")

    def test_card_and_door_stay_open(self) -> None:
        lowered = self.card.lower()
        self.assertIn("fresh package", lowered)
        self.assertIn("clone-stamped", lowered)
        self.assertIn("marketing stays with bryce", lowered)
        self.assertIn("do not invent stripe", lowered)
        self.assertNotIn("authentication required", lowered)
        self.assertNotIn("<form", self.door.lower())
        self.assertNotIn('type="password"', self.door.lower())
        self.assertNotIn("login form", self.door.lower())
        self.assertIn("password", self.door.lower())
        self.assertIn("BUSINESS_PACKS.json", self.door)

    def test_cli_json(self) -> None:
        payload = json.dumps(
            [
                {
                    "sale_id": "sale-a",
                    "assets_sha256": "aa" * 32,
                    "ops_sha256": "bb" * 32,
                }
            ]
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_unique.py"),
                "--sales-json",
                payload,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["law_id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(data["sales"][0]["verdict"], "UNIQUE")
        self.assertIs(data["commons_admission"], False)


if __name__ == "__main__":
    unittest.main()
