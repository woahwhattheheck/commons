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
        self.assertNotIn("337 NO", self.door)

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
        self.assertIn('name="robots"', self.door)
        self.assertIn("index, follow", self.door)
        self.assertIn("BUSINESS_PACKS.json", self.door)
        self.assertIn("similar", self.door.lower())
        self.assertIn("mystery", self.door.lower())
        self.assertIn("not a lottery", self.door.lower())
        self.assertIn("odds", self.door.lower())
        self.assertIn("similar is not a clone", self.card.lower())
        self.assertIn("mystery", self.card.lower())
        self.assertNotIn("stripe.com", self.door.lower())

    def test_shared_template_and_vertical_are_not_clone_when_instance_differs(self) -> None:
        sales = [
            {
                "sale_id": "sale-a",
                "template_id": "yard-card",
                "vertical": "print",
                "assets_sha256": "aa" * 32,
                "brand": "acme-lawn",
                "checkout": "owner-ck-a",
                "instructions": "acme-start",
                "ops_sha256": "bb" * 32,
            },
            {
                "sale_id": "sale-b",
                "template_id": "yard-card",
                "vertical": "print",
                "assets_sha256": "aa" * 32,
                "brand": "beta-cards",
                "checkout": "owner-ck-b",
                "instructions": "beta-start",
                "ops_sha256": "bb" * 32,
            },
        ]
        result = unique.classify_sales(sales)
        self.assertIs(result["similar_is_not_clone"], True)
        self.assertFalse(result["clone_stamp"])
        self.assertEqual(result["unique_count"], 2)
        self.assertTrue(unique.marketing_uniqueness_ok(sales[0], sales))
        self.assertEqual(result["sales"][0]["template_id"], "yard-card")
        self.assertIn("template_id", result["shared_not_clone"])
        self.assertIn("vertical", result["shared_not_clone"])

    def test_same_instance_fields_are_clone_even_with_different_template(self) -> None:
        sales = [
            {
                "sale_id": "sale-a",
                "template_id": "yard-card",
                "vertical": "print",
                "assets_sha256": "aa" * 32,
                "brand": "acme-lawn",
                "checkout": "owner-ck-a",
                "instructions": "acme-start",
                "ops_sha256": "bb" * 32,
            },
            {
                "sale_id": "sale-b",
                "template_id": "other-family",
                "vertical": "print",
                "assets_sha256": "aa" * 32,
                "brand": "acme-lawn",
                "checkout": "owner-ck-a",
                "instructions": "acme-start",
                "ops_sha256": "bb" * 32,
            },
        ]
        result = unique.classify_sales(sales)
        self.assertTrue(result["clone_stamp"])
        verdicts = {row["sale_id"]: row["verdict"] for row in result["sales"]}
        self.assertEqual(verdicts["sale-a"], "CLONE_STAMP")
        self.assertEqual(verdicts["sale-b"], "CLONE_STAMP")
        self.assertFalse(unique.marketing_uniqueness_ok(sales[0], sales))

    def test_compose_similar_mystery_does_not_remint_unique_id(self) -> None:
        compose = self.law["compose"]
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(compose["id"], "cursor-business-packs-similar-mystery-20260902-01")
        self.assertEqual(compose["source_slack_ts"], "1788323180.640899")
        self.assertEqual(self.law["uniqueness"]["instance_distinct"], ["assets", "brand", "checkout", "instructions"])
        self.assertEqual(self.law["uniqueness"]["shared_not_clone"], ["template_id", "vertical"])
        self.assertIs(self.law["similar_is_not_clone"], True)
        self.assertIs(self.law["mystery"]["not_lottery"], True)
        self.assertIs(self.law["mystery"]["not_gambling"], True)
        self.assertIs(self.law["mystery"]["fake_scarcity"], False)
        self.assertIs(self.law["mystery"]["invented_odds"], False)
        self.assertIsNone(self.law["mystery"]["value_range"])
        self.assertEqual(self.law["mystery"]["value_range_set_by"], "BRYCE")

    def test_factory_pointer_cites_goat_scaffold_without_stealing(self) -> None:
        pointer = self.law["factory_pointer"]
        self.assertEqual(pointer["id"], "cursor-business-packs-factory-pointer-20260902-01")
        self.assertEqual(pointer["scaffold_receipt"], "goat-business-packs-ready-20260902-01")
        self.assertEqual(pointer["sku"], "land/sku-business-packs-20260902.md")
        self.assertEqual(pointer["empty_slot"], "packs/_template/")
        self.assertEqual(pointer["keep_sell_door"], "keep-sell.html")
        self.assertEqual(pointer["checkout"], "NOT_MINTED")
        self.assertIs(pointer["did_not_rewrite_scaffold"], True)
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(self.law["compose"]["id"], "cursor-business-packs-similar-mystery-20260902-01")
        self.assertTrue((ROOT / "packs" / "_template" / "README.md").is_file())
        self.assertTrue((ROOT / "land" / "sku-business-packs-20260902.md").is_file())
        self.assertTrue((ROOT / "keep-sell.html").is_file())
        self.assertTrue((ROOT / "p" / "goat-business-packs-ready-20260902-01.md").is_file())
        lowered_door = self.door.lower()
        self.assertIn("packs/_template/", lowered_door)
        self.assertIn("keep-sell.html", lowered_door)
        self.assertIn("not_minted", lowered_door)
        self.assertIn("packs/_template/", self.card)
        self.assertIn("keep-sell.html", self.card)
        self.assertIn("NOT_MINTED", self.card)

    def test_mystery_pool_ok_without_invented_odds(self) -> None:
        pool = {
            "not_lottery": True,
            "not_gambling": True,
            "fake_scarcity": False,
            "value_range_owner": "BRYCE",
            "value_range": "OWNER_PROVIDED_RANGE",
            "framing": "fun generous gesture from TokenJunkieLabs",
        }
        result = unique.classify_mystery_pool(pool)
        self.assertIs(result["gate"], False)
        self.assertIs(result["commons_admission"], False)
        self.assertEqual(result["verdict"], "MYSTERY_OK")
        self.assertFalse(result["invented_odds"])
        self.assertFalse(result["lottery_framing"])
        law_pool = unique.classify_mystery_pool(self.law["mystery"])
        self.assertEqual(law_pool["verdict"], "MYSTERY_OK")
        self.assertFalse(law_pool["invented_odds"])

    def test_invented_odds_and_lottery_framing_are_flagged_not_gates(self) -> None:
        odds = unique.classify_mystery_pool(
            {
                "odds_table": {"nuts": "do-not-invent"},
                "not_lottery": True,
                "not_gambling": True,
                "value_range_owner": "BRYCE",
            }
        )
        self.assertEqual(odds["verdict"], "INVENTED_ODDS")
        self.assertTrue(odds["invented_odds"])
        self.assertIs(odds["gate"], False)
        lottery = unique.classify_mystery_pool({"framing": "this is a lottery jackpot"})
        self.assertEqual(lottery["verdict"], "LOTTERY_FRAMING")
        self.assertTrue(lottery["lottery_framing"])
        self.assertIs(lottery["commons_admission"], False)
        scarcity = unique.classify_mystery_pool(
            {
                "fake_scarcity": True,
                "not_lottery": True,
                "not_gambling": True,
                "value_range_owner": "BRYCE",
            }
        )
        self.assertEqual(scarcity["verdict"], "FAKE_SCARCITY")
        stolen_range = unique.classify_mystery_pool(
            {"value_range": "OWNER_PROVIDED_RANGE", "value_range_owner": "AGENT"}
        )
        self.assertEqual(stolen_range["verdict"], "VALUE_RANGE_NOT_BRYCE")

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
        self.assertEqual(data["composed_id"], "cursor-business-packs-similar-mystery-20260902-01")
        self.assertEqual(data["sales"][0]["verdict"], "UNIQUE")
        self.assertIs(data["commons_admission"], False)
        self.assertIs(data["similar_is_not_clone"], True)
        self.assertEqual(data["mystery"]["verdict"], "MYSTERY_OK")
        self.assertIs(data["not_lottery"], True)

    def test_sell_instance_sell_without_brand_or_door_is_missing(self) -> None:
        result = unique.classify_sell_offer(
            {
                "keep_or_sell": "SELL",
                "template_id": "yard-card",
                "assets_sha256": "aa" * 32,
            }
        )
        self.assertEqual(result["verdict"], "MISSING_INSTANCE_FOR_PRICE")
        self.assertIs(result["gate"], False)
        self.assertIs(result["commons_admission"], False)
        self.assertIs(result["agents_spend_ads"], False)
        self.assertIs(result["did_not_steal_goat_yard_card"], True)
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertIn("brand", result["missing_instance"])
        self.assertIn("door", result["missing_instance"])

    def test_sell_instance_with_brand_and_checkout_is_ok(self) -> None:
        result = unique.classify_sell_offer(
            {
                "keep_or_sell": "SELL",
                "brand": "weekend-tyler-route",
                "checkout": "owner-pastes-later",
            }
        )
        self.assertEqual(result["verdict"], "UNIQUE_INSTANCE_SELL_OK")
        self.assertTrue(result["has_brand"])
        self.assertTrue(result["has_door"])
        self.assertEqual(result["missing_instance"], [])

    def test_kit_without_instance_is_not_unique_sell(self) -> None:
        result = unique.classify_sell_offer(
            {
                "kit_not_unique_instance": True,
                "template_id": "yard-card",
            }
        )
        self.assertEqual(result["verdict"], "KIT_NOT_UNIQUE_INSTANCE")
        self.assertIs(result["gate"], False)

    def test_copy_prices_and_time_ok_earnings_flagged(self) -> None:
        ok = unique.classify_copy("$40 per bin-out, two hours Saturday")
        self.assertEqual(ok["verdict"], "COPY_OK")
        self.assertFalse(ok["earnings_claim"])
        self.assertIs(ok["agents_spend_ads"], False)
        bad = unique.classify_copy("Make $200 this weekend")
        self.assertEqual(bad["verdict"], "EARNINGS_CLAIM")
        self.assertTrue(bad["earnings_claim"])
        self.assertIs(bad["gate"], False)

    def test_sell_instance_law_does_not_steal_or_remint(self) -> None:
        block = self.law["sell_instance"]
        self.assertEqual(block["id"], "cursor-business-packs-sell-instance-20260902-01")
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(block["source_slack_ts"], "1788326387.638969")
        self.assertEqual(block["source_channel_id"], "C0BU7JAPUH3")
        self.assertEqual(block["scout_demand_id"], "scout-demand-yard-card-instance-20260902-01")
        self.assertIs(block["did_not_remint_scout_demand"], True)
        self.assertIs(block["did_not_steal_goat_yard_card"], True)
        self.assertIs(block["did_not_write_buyer_tiers"], True)
        self.assertIs(block["agents_spend_ads"], False)
        self.assertEqual(block["checkout"], "NOT_MINTED")
        self.assertEqual(block["named_unique_sell_requires"], ["brand", "door"])
        self.assertEqual(block["copy"], "prices_and_time_budgets_never_earnings")
        self.assertIn("named unique-instance SELL", self.card)
        self.assertIn("never earnings", self.door)
        self.assertIn("password", self.door)
        self.assertNotIn("<form", self.door)
        self.assertNotIn("337 NO", json.dumps(block))
        self.assertNotIn("337 NO", self.card)
        self.assertTrue((ROOT / "host" / "pack_keep_sell_candidate.py").is_file())
        self.assertTrue((ROOT / "p" / "cursor-business-pack-yard-card-20260902-01.md").is_file())

    def test_thanks_pixel_pointer_is_empty_owner_paste(self) -> None:
        block = self.law["thanks_pixel"]
        self.assertEqual(block["id"], "cursor-business-pack-thanks-pixel-20260902-01")
        self.assertEqual(block["pixel_id"], "")
        self.assertEqual(block["door"], "packs/thanks.html")
        self.assertIs(block["agents_spend_ads"], False)
        self.assertIs(block["agents_mint_pixel_id"], False)
        self.assertIs(block["did_not_remint_scout_demand"], True)
        self.assertIn("packs/thanks.html", self.door)
        self.assertIn("thank-you door", self.card)

    def test_waitlist_pointer_does_not_steal_or_remint(self) -> None:
        block = self.law["waitlist"]
        self.assertEqual(block["id"], "cursor-business-pack-waitlist-pointer-20260902-01")
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(
            block["scout_demand_id"],
            "scout-demand-pack-door-waitlist-20260902-01",
        )
        self.assertIs(block["did_not_remint_scout_demand"], True)
        self.assertIs(block["did_not_write_waitlist_paths"], True)
        self.assertIs(block["did_not_overwrite_thanks_html"], True)
        self.assertIs(block["did_not_steal_desk_helper"], True)
        self.assertIs(block["did_not_wrap_harborline"], True)
        self.assertEqual(block["claimed_by"], "bc-31c8ef9a")
        self.assertEqual(block["door"], "packs/waitlist.html")
        self.assertEqual(block["checkout"], "NOT_MINTED")
        self.assertIs(block["agents_spend_ads"], False)
        self.assertIs(block["waitlist_door_landed"], True)
        self.assertEqual(block["waitlist_href"], "packs/waitlist.html")
        self.assertIs(block["did_not_overwrite_waitlist_html"], True)
        self.assertTrue((ROOT / "packs" / "waitlist.html").is_file())
        self.assertIn('href="./packs/waitlist.html"', self.door)
        self.assertNotIn("<form", self.door)
        self.assertIn("waitlist", self.door.lower())
        self.assertIn("waitlist", self.card.lower())
        self.assertIn("password", self.door)
        self.assertNotIn("<form", self.door)
        self.assertNotIn("337 NO", json.dumps(block))
        self.assertNotIn("337 NO", self.card)
        self.assertTrue(
            (ROOT / "p" / "cursor-business-pack-waitlist-pointer-20260902-01.md").is_file()
        )
        self.assertTrue(
            (ROOT / "p" / "cursor-business-pack-waitlist-href-20260902-01.md").is_file()
        )
        self.assertNotEqual(block["id"], block["scout_demand_id"])
        self.assertEqual(
            block["pointer_helper"],
            "host/business_pack_waitlist_pointer.py",
        )
        self.assertEqual(
            block["pointer_helper_receipt"],
            "cursor-business-pack-waitlist-pointer-helper-20260902-01",
        )
        self.assertEqual(block["pointer_helper_claimed_by"], "bc-078225d9")
        self.assertIs(block["did_not_remint_pointer_helper"], True)
        self.assertIs(block["did_not_write_pointer_helper_paths"], True)
        self.assertEqual(block["files_owner"], "bc-31c8ef9a")
        self.assertEqual(block["excluded_state_shows"], "waitlist_not_checkout")
        self.assertTrue(
            (ROOT / "host" / "business_pack_waitlist_pointer.py").is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "p"
                / "cursor-business-pack-waitlist-pointer-helper-20260902-01.md"
            ).is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "p"
                / "cursor-business-pack-waitlist-helper-pointer-20260902-01.md"
            ).is_file()
        )
        self.assertNotEqual(
            block["id"],
            block["pointer_helper_receipt"],
        )

    def test_instance_catalog_points_without_stealing_files(self) -> None:
        block = self.law["instances"]
        self.assertEqual(block["id"], "cursor-business-pack-instance-catalog-20260902-01")
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(block["keep_sell_ledger"], "not_this_seat")
        self.assertIs(block["did_not_write_keep_sell_ledger"], True)
        self.assertIs(block["did_not_steal_instance_files"], True)
        self.assertIs(block["did_not_steal_desk_helper"], True)
        self.assertIs(block["did_not_wrap_harborline"], True)
        self.assertIs(block["did_not_write_plant_instance"], True)
        self.assertEqual(block["shared_desk_helper"], "host/business_pack_desk_instance.py")
        self.assertEqual(block["shared_desk_helper_owner"], "TALLY")
        self.assertEqual(
            block["shared_desk_helper_pointer"],
            "cursor-business-pack-shared-desk-helper-pointer-20260902-01",
        )
        self.assertEqual(block["harborline_wrap_sha"], "58fef5dd3")
        self.assertEqual(block["harborline_waitlist_slot_sha"], "08aabf097")
        self.assertEqual(
            block["harborline_waitlist_slot_pointer"],
            "cursor-business-pack-harborline-waitlist-slot-pointer-20260902-01",
        )
        self.assertIs(block["did_not_overwrite_waitlist_html"], True)
        self.assertEqual(block["checkout"], "NOT_MINTED")
        doors = [row["door"] for row in block["landed"]]
        self.assertEqual(
            doors,
            [
                "packs/lotribbon-greetings-20260902-01/index.html",
                "packs/sidewalk-signal-web-desk-20260902-01/index.html",
                "packs/desk-website-service-20260902-01/door.html",
            ],
        )
        for rel in doors:
            self.assertTrue((ROOT / rel).is_file(), rel)
            self.assertIn(rel.replace("packs/", "./packs/"), self.door)
        self.assertIn("LotRibbon Greetings", self.door)
        self.assertIn("Sidewalk Signal", self.door)
        self.assertIn("Harborline Local Sites", self.door)
        self.assertIn("password", self.door)
        self.assertNotIn("<form", self.door)
        self.assertNotIn("337 NO", json.dumps(block))
        helpers = [row.get("helper") for row in block["landed"] if row["tier"] == "DESK"]
        self.assertEqual(
            helpers,
            [
                "host/business_pack_desk_instance.py",
                "host/business_pack_desk_instance.py",
            ],
        )
        harborline = [row for row in block["landed"] if row["brand"] == "Harborline Local Sites"][0]
        self.assertEqual(harborline["waitlist"], "packs/waitlist.html")
        self.assertIn("host/business_pack_desk_instance.py", self.door)
        self.assertTrue(
            (ROOT / "p" / "cursor-business-pack-instance-catalog-20260902-01.md").is_file()
        )
        self.assertTrue(
            (ROOT / "p" / "cursor-business-pack-shared-desk-helper-pointer-20260902-01.md").is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "p"
                / "cursor-business-pack-harborline-waitlist-slot-pointer-20260902-01.md"
            ).is_file()
        )

    def test_rating_slot_pointer_is_empty_owner_paste(self) -> None:
        block = self.law["rating_slot"]
        self.assertEqual(block["id"], "cursor-business-pack-rating-slot-20260902-01")
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(block["source_slack_ts"], "1788327092.565209")
        self.assertEqual(block["badge_url"], "")
        self.assertEqual(block["report_url"], "")
        self.assertEqual(block["partner_name"], "OWNER_UNSET")
        self.assertEqual(block["bulk_price"], "OWNER_UNSET")
        self.assertEqual(block["forbidden"], "dollar_valuation")
        self.assertIs(block["did_not_write_scout_advertising_general"], True)
        self.assertIs(block["did_not_write_king_county_lims"], True)
        self.assertEqual(block["checkout"], "NOT_MINTED")
        self.assertIn("rating", self.door.lower())
        self.assertIn("dollar valuation", self.card.lower())
        self.assertIn("password", self.door)
        self.assertNotIn("<form", self.door)
        self.assertNotIn("337 NO", json.dumps(block))
        self.assertTrue((ROOT / "host" / "business_pack_rating.py").is_file())
        self.assertTrue((ROOT / "packs" / "_template" / "rating.md").is_file())
        self.assertTrue(
            (ROOT / "p" / "cursor-business-pack-rating-slot-20260902-01.md").is_file()
        )


if __name__ == "__main__":
    unittest.main()
