#!/usr/bin/env python3
"""Pack paperwork checklist. Not legal advice. Not a Commons gate."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_paperwork as paper  # noqa: E402


COMPLETE = {
    "registration": "file DBA in the county named on the instance",
    "ein": "IRS EIN confirmation letter on file",
    "sales_tax": "state permit number pasted by owner",
    "license": "city license pasted by owner",
    "insurance": "GL cert on file, owner-reviewed",
    "contract": "instance contract with OWNER/COUNSEL markers",
}


class BusinessPackPaperworkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = paper.load_law()
        self.card = (ROOT / "ground" / "BUSINESS_PACK_PAPERWORK.md").read_text(
            encoding="utf-8"
        )
        self.sheet = (ROOT / "packs" / "_template" / "paperwork.md").read_text(
            encoding="utf-8"
        )
        self.day = (ROOT / "packs" / "_template" / "day.md").read_text(encoding="utf-8")
        self.offer = (ROOT / "packs" / "_template" / "offer.md").read_text(
            encoding="utf-8"
        )
        self.unique = json.loads(
            (ROOT / "ground" / "BUSINESS_PACKS.json").read_text(encoding="utf-8")
        )

    def test_law_is_not_a_commons_gate(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-pack-paperwork-20260902-01")
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertEqual(self.law["source_slack_ts"], "1788327816.150299")
        self.assertEqual(
            self.law["required"],
            ["registration", "ein", "sales_tax", "license", "insurance", "contract"],
        )
        self.assertIs(self.law["legal_advice"], False)
        self.assertIs(self.law["hold_counsel"], True)
        self.assertIs(self.law["did_not_write_plant_instance"], True)
        self.assertIs(self.law["did_not_write_desk_instance"], True)
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        dumped = json.dumps(self.law)
        self.assertNotIn("337 NO", dumped)
        self.assertNotIn("337 NO", self.card)
        self.assertNotIn("337 NO", self.sheet)
        self.assertNotIn("buy.stripe.com", self.sheet.lower())

    def test_incomplete_without_checklist(self) -> None:
        result = paper.classify_paperwork({"registration": "DBA filed"})
        self.assertEqual(result["verdict"], "PAPERWORK_INCOMPLETE")
        self.assertIn("ein", result["missing"])
        self.assertIs(result["legal_advice"], False)
        self.assertIs(result["gate"], False)
        self.assertIs(result["commons_admission"], False)

    def test_complete_checklist_is_ok_and_still_hold_counsel(self) -> None:
        result = paper.classify_paperwork(COMPLETE)
        self.assertEqual(result["verdict"], "PAPERWORK_OK")
        self.assertEqual(result["missing"], [])
        self.assertIs(result["hold_counsel"], True)
        self.assertIs(result["not_legal_advice"], True)

    def test_invented_stripe_url_is_flagged(self) -> None:
        packed = dict(COMPLETE)
        packed["contract"] = "sign then pay https://buy.stripe.com/fake"
        result = paper.classify_paperwork(packed)
        self.assertEqual(result["verdict"], "PAPERWORK_INVENTED_URL")
        self.assertTrue(result["invented_url"])
        self.assertIs(result["commons_admission"], False)

    def test_earnings_in_ads_flagged(self) -> None:
        packed = dict(COMPLETE)
        packed["ads_copy"] = "Make $200 this weekend"
        result = paper.classify_paperwork(packed)
        self.assertEqual(result["verdict"], "EARNINGS_IN_ADS")
        self.assertTrue(result["earnings_in_ads"])
        self.assertIs(result["gate"], False)

    def test_sheet_is_a_do_x_list(self) -> None:
        self.assertIn("Do X", self.sheet)
        self.assertIn("OWNER_UNSET", self.sheet)
        self.assertIn("HOLD_COUNSEL", self.sheet)
        self.assertIn("not a Commons seat", self.sheet)
        self.assertIn("EIN", self.sheet)
        self.assertIn("insurance", self.sheet.lower())
        self.assertIn("contract", self.sheet.lower())
        self.assertIn("not legal advice", self.sheet.lower())
        self.assertIn("paperwork", self.day.lower())
        self.assertIn("paperwork", self.offer.lower())

    def test_unique_pack_pointer_does_not_remint(self) -> None:
        block = self.unique["paperwork"]
        self.assertEqual(block["id"], "cursor-business-pack-paperwork-20260902-01")
        self.assertEqual(self.unique["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(
            self.unique["operator_day"]["id"],
            "cursor-business-pack-operator-day-20260902-01",
        )
        self.assertEqual(
            self.unique["running_cost"]["id"],
            "cursor-business-pack-running-cost-20260902-01",
        )
        self.assertIs(block["did_not_write_plant_instance"], True)

    def test_cli(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_paperwork.py"),
                "--pack-json",
                json.dumps(COMPLETE),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "PAPERWORK_OK")
        self.assertEqual(payload["law_id"], "cursor-business-pack-paperwork-20260902-01")


if __name__ == "__main__":
    unittest.main()
