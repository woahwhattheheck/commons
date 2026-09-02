#!/usr/bin/env python3
"""LotRibbon $1000 plant instance: unique door, costed inventory, no invented slots."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_plant_instance as plant  # noqa: E402
import business_pack_unique as unique  # noqa: E402


class BusinessPackPlantInstanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = plant.load_law()
        self.base = ROOT / "packs" / "lotribbon-greetings-20260902-01"
        self.door = (self.base / "index.html").read_text(encoding="utf-8")
        self.offer = (self.base / "offer.md").read_text(encoding="utf-8")
        self.receipt = (
            ROOT / "p" / "cursor-plant-yard-greeting-pack-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.land = (ROOT / "land" / "plant-yard-greeting-20260902.md").read_text(
            encoding="utf-8"
        )

    def test_law_is_not_a_commons_gate(self) -> None:
        self.assertEqual(self.law["id"], "cursor-plant-yard-greeting-pack-20260902-01")
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertEqual(self.law["source_slack_ts"], "1788326371.557759")
        self.assertEqual(self.law["claim_slack_ts"], "1788327783.673689")
        self.assertEqual(
            self.law["matched_demand_id"],
            "scout-demand-plant-yard-greeting-pack-20260902-01",
        )
        self.assertIs(self.law["did_not_remint_scout_demand"], True)
        self.assertEqual(self.law["brand"], "LotRibbon Greetings")
        self.assertEqual(self.law["tier_usd"], 1000)
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        self.assertEqual(self.law["running_cost"], "OWNER_UNSET")
        self.assertEqual(self.law["profit_share_percent"], "OWNER_UNSET")
        self.assertEqual(self.law["partial_ownership_fraction"], "OWNER_UNSET")
        self.assertIs(self.law["saleable"], False)
        self.assertIs(self.law["did_not_write_thanks_html"], True)
        self.assertIs(self.law["did_not_rewrite_goat_template"], True)
        dumped = json.dumps(self.law)
        self.assertNotIn("337 NO", dumped)
        self.assertNotIn("337 NO", self.door)
        self.assertNotIn("337 NO", self.receipt)

    def test_live_instance_classifies_ok_but_not_factory_saleable(self) -> None:
        result = plant.classify_instance()
        self.assertEqual(result["verdict"], "PLANT_INSTANCE_OK")
        self.assertIs(result["gate"], False)
        self.assertIs(result["saleable"], False)
        self.assertTrue(result["tos_blocks_factory_sale"])
        self.assertEqual(result["tos"]["verdict"], "TOS_INCOMPLETE")
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertEqual(result["running_cost"], "OWNER_UNSET")
        self.assertEqual(result["sell_instance"]["verdict"], "UNIQUE_INSTANCE_SELL_OK")
        self.assertEqual(result["unique"], "UNIQUE")
        self.assertTrue(result["ops_sell_checklist"])
        self.assertEqual(result["inventory"]["item_count"], 20)
        self.assertEqual(result["inventory"]["planning_total_usd"], "1067.50")
        self.assertEqual(result["operator"]["verdict"], "OPERATOR_DAY_OK")
        self.assertEqual(result["operator"]["support_price"], "OWNER_UNSET")
        self.assertEqual(result["running_cost_class"]["verdict"], "RUNNING_COST_OK")
        self.assertIs(result["sold_once"], True)
        self.assertEqual(
            result["sold_once_badge"],
            "Instance 1 of 1. This brand, this domain, this door are sold once.",
        )
        self.assertEqual(result["plant_anchor_slot"], "OWNER_UNSET")

    def test_door_is_named_lawn_greeting_not_yard_card(self) -> None:
        self.assertIn("LotRibbon", self.door)
        self.assertIn("index,follow", self.door.replace(" ", ""))
        self.assertIn("OWNER_PASTE_REQUIRED", self.door)
        self.assertIn("NOT_MINTED", self.door)
        self.assertIn("OWNER_UNSET", self.door)
        self.assertIn("We did most of the work", self.door)
        self.assertNotIn("yard card", self.door.lower())
        self.assertNotIn("yard-card", self.door.lower())
        self.assertNotRegex(self.door, r"(?i)\bfranchis")
        self.assertNotRegex(self.offer, r"(?i)\bfranchis")
        self.assertNotIn("buy.stripe.com", self.door)
        self.assertNotIn("<form", self.door.lower())
        self.assertNotIn('type="password"', self.door.lower())
        self.assertNotIn("<script src=", self.door.lower())
        self.assertIn("TikTok", self.door)
        self.assertIn("Instagram", self.door)
        self.assertIn("Pinterest", self.door)
        self.assertIn(
            "Instance 1 of 1. This brand, this domain, this door are sold once.",
            self.door,
        )
        self.assertIn('data-sold-once="true"', self.door)
        self.assertIn('data-owner-slot="plant-anchor"', self.door)
        self.assertNotRegex(self.door, r"(?i)no royalty")
        self.assertNotIn("become a business owner", self.door.lower())

    def test_public_copy_has_no_for_this_price_line(self) -> None:
        public = plant.public_copy()
        self.assertNotRegex(public, r"(?i)for this price")
        self.assertNotRegex(public, r"(?i)for \$\d")
        self.assertNotRegex(public, r"(?i)become (?:a )?business owner")
        self.assertNotRegex(public, r"(?i)become your own boss")
        copy = unique.classify_copy(public)
        self.assertEqual(copy["verdict"], "COPY_OK")

    def test_inventory_rows_are_costed(self) -> None:
        data = plant.load_inventory()
        report = plant.inventory_report(data)
        self.assertTrue(report["ok"], report["errors"])
        self.assertGreaterEqual(report["item_count"], 12)
        self.assertLessEqual(report["item_count"], 20)
        self.assertIs(data["planning_not_owner_pasted_running_cost"], True)

    def test_missing_files_verdict(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "packs" / "lotribbon-greetings-20260902-01").mkdir(parents=True)
            (root / "ground").mkdir()
            (root / "ground" / "BUSINESS_PACK_PLANT.json").write_text(
                json.dumps(self.law), encoding="utf-8"
            )
            result = plant.classify_instance(root)
            self.assertEqual(result["verdict"], "MISSING_FILES")
            self.assertIn("index.html", result["missing_files"])

    def test_franchise_vocab_on_door_is_flagged(self) -> None:
        text = plant.public_copy() + "\njoin our franchise network\n"
        self.assertTrue(plant.FRANCHISE_RE.search(text))

    def test_receipt_does_not_remint_or_steal(self) -> None:
        self.assertIn("did_not_remint_scout_demand: true", self.receipt)
        self.assertIn("scout-demand-plant-yard-greeting-pack-20260902-01", self.receipt)
        self.assertIn("cursor-plant-yard-greeting-pack-20260902-01", self.receipt)
        self.assertIn("NOT_MINTED", self.receipt)
        self.assertIn("OWNER_UNSET", self.receipt)
        self.assertIn("not filing", (self.base / "paperwork.md").read_text(encoding="utf-8"))
        self.assertIn("HOLD_COUNSEL", (self.base / "paperwork.md").read_text(encoding="utf-8"))

    def test_cli(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "business_pack_plant_instance.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "PLANT_INSTANCE_OK")
        self.assertEqual(payload["id"], "cursor-plant-yard-greeting-pack-20260902-01")
        self.assertIs(payload["sold_once"], True)

    def test_sold_once_checks_reject_mismatch_badge_and_royalty(self) -> None:
        html = (
            "Instance 1 of 1. This brand, this domain, this door are sold once."
            '<p data-owner-slot="plant-anchor"><code>OWNER_UNSET</code></p>'
        )
        ok = plant.sold_once_checks(
            unique="UNIQUE",
            manifest_sold_once=True,
            door_html=html,
        )
        self.assertTrue(ok["ok"])
        mismatch = plant.sold_once_checks(
            unique="UNIQUE",
            manifest_sold_once=False,
            door_html=html,
        )
        self.assertEqual(mismatch["verdict"], "SOLD_ONCE_MISMATCH")
        missing = plant.sold_once_checks(
            unique="UNIQUE",
            manifest_sold_once=True,
            door_html='<p data-owner-slot="plant-anchor">OWNER_UNSET</p>',
        )
        self.assertEqual(missing["verdict"], "SOLD_ONCE_BADGE_MISSING")
        slot = plant.sold_once_checks(
            unique="UNIQUE",
            manifest_sold_once=True,
            door_html="Instance 1 of 1. This brand, this domain, this door are sold once.",
        )
        self.assertEqual(slot["verdict"], "PLANT_ANCHOR_SLOT_MISSING")
        royalty = plant.sold_once_checks(
            unique="UNIQUE",
            manifest_sold_once=True,
            door_html=html + " No royalty. Sold once.",
        )
        self.assertEqual(royalty["verdict"], "ROYALTY_CLAIM_BEFORE_TOS")
        match_flag = plant.sold_once_checks(
            unique="MATCH",
            manifest_sold_once=True,
            door_html="Built from the same method as our sold instances.",
        )
        self.assertEqual(match_flag["verdict"], "SOLD_ONCE_MISMATCH")
        match_ok = plant.sold_once_checks(
            unique="MATCH",
            manifest_sold_once=False,
            door_html="Built from the same method as our sold instances.",
        )
        self.assertTrue(match_ok["ok"])
        self.assertEqual(
            match_ok["sold_once_badge"],
            "Built from the same method as our sold instances.",
        )

    def test_manifest_sold_once_matches_unique_and_copy_stays_ok(self) -> None:
        self.assertIs(plant.load_manifest()["sold_once"], True)
        copy = unique.classify_copy(self.door)
        self.assertEqual(copy["verdict"], "COPY_OK")
        self.assertNotIn("creative_brief.md", plant.REQUIRED_FILES)

    def test_instance_creative_brief_is_research_not_live_royalty(self) -> None:
        brief = (self.base / "assets" / "creative_brief.md").read_text(encoding="utf-8")
        self.assertIn("OWNER_UNSET", brief)
        self.assertIn("$1,000", brief)
        self.assertIn("It has a name. It has a door. It's sold once.", brief)
        self.assertIn("A business, built and documented. Yours outright.", brief)
        self.assertIn("ad-research", brief.lower())
        self.assertNotRegex(brief, r"(?i)make \$\d")
        self.assertNotRegex(brief, r"(?i)earn \$\d")
        self.assertNotIn("10,350", brief)
        self.assertNotIn("packs/_template/creative_brief.md", brief)
        template = ROOT / "packs" / "_template" / "creative_brief.md"
        self.assertFalse(template.exists())


if __name__ == "__main__":
    unittest.main()
