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


if __name__ == "__main__":
    unittest.main()
