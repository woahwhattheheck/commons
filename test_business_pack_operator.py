#!/usr/bin/env python3
"""Employee-day runbook for sold packs. Support sub is not a Commons gate."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_operator as op  # noqa: E402


class BusinessPackOperatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = op.load_law()
        self.card = (ROOT / "ground" / "BUSINESS_PACK_OPERATOR.md").read_text(
            encoding="utf-8"
        )
        self.day = (ROOT / "packs" / "_template" / "day.md").read_text(encoding="utf-8")
        self.unique = json.loads(
            (ROOT / "ground" / "BUSINESS_PACKS.json").read_text(encoding="utf-8")
        )

    def test_law_is_not_a_commons_gate(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-pack-operator-day-20260902-01")
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertEqual(self.law["source_slack_ts"], "1788327136.593709")
        self.assertEqual(self.law["treat_customer_as"], "employee")
        self.assertEqual(self.law["support"]["paid_subscription_to"], "tjlabs")
        self.assertEqual(self.law["support"]["price"], "OWNER_UNSET")
        self.assertIs(self.law["support"]["commons_admission"], False)
        self.assertIs(self.law["did_not_write_lead_tos_paths"], True)
        self.assertIs(self.law["did_not_invent_percent_or_equity"], True)
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        self.assertNotIn("337 NO", json.dumps(self.law))
        self.assertNotIn("337 NO", self.card)
        self.assertNotIn("337 NO", self.day)
        self.assertNotIn("TJLABS_PACK_TERMS", json.dumps(self.law))

    def test_incomplete_without_do_x_list(self) -> None:
        result = op.classify_operator({"onboarding": "day 0", "training": "hour 1"})
        self.assertEqual(result["verdict"], "OPERATOR_INCOMPLETE")
        self.assertIn("daily_tasks", result["missing"])
        self.assertIs(result["gate"], False)
        self.assertIs(result["commons_admission"], False)

    def test_complete_employee_day(self) -> None:
        result = op.classify_operator(
            {
                "onboarding": "watch the start sheet",
                "training": "run the two-hour walk once with the trainer list",
                "daily_tasks": ["do the route", "log the bins", "send the invoice"],
            }
        )
        self.assertEqual(result["verdict"], "OPERATOR_DAY_OK")
        self.assertEqual(result["daily_task_count"], 3)
        self.assertEqual(result["support_price"], "OWNER_UNSET")
        self.assertEqual(result["fail_to_profit_framing"], "owner_runbook_not_ad_copy")

    def test_invented_support_price_is_flagged(self) -> None:
        result = op.classify_operator(
            {
                "onboarding": "a",
                "training": "b",
                "daily_tasks": ["do x"],
                "support_price_usd": 49,
            }
        )
        self.assertEqual(result["verdict"], "SUPPORT_PRICE_INVENTED")
        self.assertTrue(result["support_price_invented"])
        self.assertIs(result["commons_admission"], False)

    def test_earnings_in_ads_flagged_runbook_ok(self) -> None:
        result = op.classify_operator(
            {
                "onboarding": "a",
                "training": "b",
                "daily_tasks": ["do x"],
                "ads_copy": "Make $200 this weekend",
            }
        )
        self.assertEqual(result["verdict"], "EARNINGS_IN_ADS")
        self.assertTrue(result["earnings_in_ads"])
        self.assertIs(result["gate"], False)

    def test_day_sheet_is_a_do_x_list(self) -> None:
        self.assertIn("Do X", self.day)
        self.assertIn("employee", self.day.lower())
        self.assertIn("tjlabs", self.day.lower())
        self.assertIn("OWNER_UNSET", self.day)
        self.assertIn("not a Commons seat", self.day)
        self.assertIn("skipped a task", self.day)

    def test_unique_pack_pointer_does_not_remint(self) -> None:
        block = self.unique["operator_day"]
        self.assertEqual(block["id"], "cursor-business-pack-operator-day-20260902-01")
        self.assertEqual(self.unique["id"], "cursor-business-packs-unique-20260902-01")
        self.assertIs(block["did_not_write_lead_tos_paths"], True)

    def test_cli(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_operator.py"),
                "--pack-json",
                json.dumps(
                    {
                        "onboarding": "a",
                        "training": "b",
                        "daily_tasks": ["do x"],
                    }
                ),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "OPERATOR_DAY_OK")
        self.assertEqual(payload["law_id"], "cursor-business-pack-operator-day-20260902-01")


if __name__ == "__main__":
    unittest.main()
