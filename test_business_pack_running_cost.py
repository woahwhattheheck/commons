#!/usr/bin/env python3
"""Running cost must ride with 'for this price'. Not a Commons gate."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_running_cost as cost  # noqa: E402


class BusinessPackRunningCostTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = cost.load_law()
        self.card = (ROOT / "ground" / "BUSINESS_PACK_RUNNING_COST.md").read_text(
            encoding="utf-8"
        )
        self.sheet = (ROOT / "packs" / "_template" / "running-cost.md").read_text(
            encoding="utf-8"
        )
        self.offer = (ROOT / "packs" / "_template" / "offer.md").read_text(
            encoding="utf-8"
        )
        self.day = (ROOT / "packs" / "_template" / "day.md").read_text(encoding="utf-8")
        self.unique = json.loads(
            (ROOT / "ground" / "BUSINESS_PACKS.json").read_text(encoding="utf-8")
        )

    def test_law_is_not_a_commons_gate(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-pack-running-cost-20260902-01")
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertEqual(self.law["source_slack_ts"], "1788327466.578309")
        self.assertEqual(self.law["running_cost"], "OWNER_UNSET")
        self.assertIs(self.law["for_this_price_requires_running_cost"], True)
        self.assertEqual(
            self.law["ownership_copy_waits_on"], "cursor-tjlabs-pack-tos-20260902-01"
        )
        self.assertIs(self.law["did_not_write_scout_messaging_angle"], True)
        self.assertIs(self.law["did_not_invent_percent_or_equity"], True)
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        dumped = json.dumps(self.law)
        self.assertNotIn("337 NO", dumped)
        self.assertNotIn("337 NO", self.card)
        self.assertNotIn("337 NO", self.sheet)
        self.assertNotIn("MESSAGING_ANGLE.md", dumped)

    def test_for_this_price_without_cost_is_expense_omitted(self) -> None:
        result = cost.classify_running_cost(
            {"copy": "become business owner for this price"}
        )
        self.assertEqual(result["verdict"], "EXPENSE_OMITTED")
        self.assertTrue(result["expense_omitted"])
        self.assertTrue(result["ownership_copy_waits"])
        self.assertIs(result["gate"], False)
        self.assertIs(result["commons_admission"], False)

    def test_price_line_with_owner_pasted_cost_is_ok(self) -> None:
        result = cost.classify_running_cost(
            {
                "copy": "yard-help kit for this price",
                "running_cost_usd": "materials + ads the buyer pays",
                "owner_pasted_running_cost": True,
            }
        )
        self.assertEqual(result["verdict"], "RUNNING_COST_OK")
        self.assertFalse(result["expense_omitted"])

    def test_invented_running_cost_is_flagged(self) -> None:
        result = cost.classify_running_cost(
            {
                "copy": "kit for this price",
                "running_cost_usd": 40,
            }
        )
        self.assertEqual(result["verdict"], "RUNNING_COST_INVENTED")
        self.assertTrue(result["running_cost_invented"])

    def test_ownership_copy_waits_on_tos(self) -> None:
        result = cost.classify_running_cost({"copy": "become your own boss"})
        self.assertEqual(result["verdict"], "OWNERSHIP_COPY_WAITS")
        self.assertTrue(result["ownership_copy_waits"])
        pasted = cost.classify_running_cost(
            {"copy": "become your own boss", "tos_owner_pasted": True}
        )
        self.assertEqual(pasted["verdict"], "RUNNING_COST_OK")

    def test_work_claim_needs_assets(self) -> None:
        result = cost.classify_running_cost(
            {"copy": "we did most of the work for you!"}
        )
        self.assertEqual(result["verdict"], "WORK_CLAIM_UNSUBSTANTIATED")
        filled = cost.classify_running_cost(
            {
                "copy": "we did most of the work for you!",
                "assets": ["door.html", "route-sheet.md"],
            }
        )
        self.assertEqual(filled["verdict"], "RUNNING_COST_OK")

    def test_earnings_still_flagged(self) -> None:
        result = cost.classify_running_cost(
            {"copy": "Make $200 this weekend for this price"}
        )
        self.assertEqual(result["verdict"], "EARNINGS_IN_ADS")
        self.assertTrue(result["earnings_in_ads"])
        self.assertIs(result["gate"], False)

    def test_sheet_and_offer_surface_the_slot(self) -> None:
        self.assertIn("for this price", self.sheet)
        self.assertIn("OWNER_UNSET", self.sheet)
        self.assertIn("running cost", self.sheet.lower())
        self.assertIn("not a Commons seat", self.sheet)
        self.assertIn("omit", self.sheet.lower())
        self.assertIn("OWNER_UNSET", self.offer)
        self.assertIn("running cost", self.offer.lower())
        self.assertIn("running cost", self.day.lower())
        self.assertIn("OWNER_UNSET", self.day)

    def test_unique_pack_pointer_does_not_remint(self) -> None:
        block = self.unique["running_cost"]
        self.assertEqual(block["id"], "cursor-business-pack-running-cost-20260902-01")
        self.assertEqual(self.unique["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(
            self.unique["operator_day"]["id"],
            "cursor-business-pack-operator-day-20260902-01",
        )
        self.assertIs(block["did_not_write_scout_messaging_angle"], True)

    def test_cli(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_running_cost.py"),
                "--offer-json",
                json.dumps({"copy": "kit for this price"}),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "EXPENSE_OMITTED")
        self.assertEqual(payload["law_id"], "cursor-business-pack-running-cost-20260902-01")


if __name__ == "__main__":
    unittest.main()
