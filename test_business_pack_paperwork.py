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
    "state": "TX",
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
            [
                "state",
                "registration",
                "ein",
                "sales_tax",
                "license",
                "insurance",
                "contract",
            ],
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
        self.assertIn("state", result["missing"])
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

    def test_paperwork_included_without_slots_is_unsubstantiated(self) -> None:
        result = paper.classify_paperwork(
            {"copy": "your own employee and employer, with the paperwork done"}
        )
        self.assertEqual(result["verdict"], "PAPERWORK_CLAIM_UNSUBSTANTIATED")
        self.assertTrue(result["included_claim"])
        self.assertTrue(result["claim_unsubstantiated"])
        self.assertIs(result["gate"], False)
        filled = dict(COMPLETE)
        filled["copy"] = "paperwork included"
        ok = paper.classify_paperwork(filled)
        self.assertEqual(ok["verdict"], "PAPERWORK_OK")
        self.assertTrue(ok["included_claim"])
        self.assertFalse(ok["claim_unsubstantiated"])

    def test_filing_as_lawyer_is_flagged_until_counsel(self) -> None:
        packed = dict(COMPLETE)
        packed["copy"] = "we filed your LLC"
        result = paper.classify_paperwork(packed)
        self.assertEqual(result["verdict"], "PAPERWORK_FILING_CLAIM")
        self.assertTrue(result["filing_as_lawyer"])
        self.assertIs(result["legal_advice"], False)
        packed["counsel_cleared"] = True
        cleared = paper.classify_paperwork(packed)
        self.assertEqual(cleared["verdict"], "PAPERWORK_OK")
        self.assertIs(cleared["hold_counsel"], False)

    def test_missing_state_is_incomplete(self) -> None:
        packed = dict(COMPLETE)
        del packed["state"]
        result = paper.classify_paperwork(packed)
        self.assertEqual(result["verdict"], "PAPERWORK_INCOMPLETE")
        self.assertIn("state", result["missing"])

    def test_door_overclaim_is_flagged(self) -> None:
        packed = dict(COMPLETE)
        packed["copy"] = "we set up your LLC"
        result = paper.classify_paperwork(packed)
        self.assertEqual(result["verdict"], "PAPERWORK_DOOR_OVERCLAIM")
        self.assertTrue(result["door_overclaim"])
        self.assertIs(result["gate"], False)

    def test_invented_partner_link_is_flagged_empty_ok(self) -> None:
        packed = dict(COMPLETE)
        packed["partner_link"] = "https://example.com/fake-formation"
        result = paper.classify_paperwork(packed)
        self.assertEqual(result["verdict"], "PARTNER_LINK_INVENTED")
        self.assertTrue(result["partner_link_invented"])
        empty = paper.classify_paperwork(COMPLETE)
        self.assertTrue(empty["partner_empty"])
        self.assertEqual(empty["verdict"], "PAPERWORK_OK")
        pasted = dict(COMPLETE)
        pasted["partner_link"] = "https://example.com/owner-pasted"
        pasted["owner_pasted_partner"] = True
        ok = paper.classify_paperwork(pasted)
        self.assertEqual(ok["verdict"], "PAPERWORK_OK")
        self.assertFalse(ok["partner_link_invented"])

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
        self.assertIn("paperwork included", self.sheet.lower())
        self.assertIn("not tjlabs doing the filing", self.sheet.lower())
        self.assertIn("paperwork", self.day.lower())
        self.assertIn("paperwork", self.offer.lower())
        self.assertNotIn("MESSAGING_ANGLE.md", json.dumps(self.law["included_claim"]))
        self.assertIn("not a national list", self.sheet.lower())
        self.assertIn("State:", self.sheet)
        self.assertIn("OWNER_UNSET", self.sheet)
        self.assertIn("we set up your LLC", self.sheet)
        self.assertIn("FTC", self.sheet)
        self.assertIs(self.law["state_instance"]["did_not_write_scout_paperwork_memo"], True)
        self.assertEqual(
            self.law["state_instance"]["partner_link"],
            "",
        )

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
        included = self.law["included_claim"]
        self.assertEqual(
            included["id"], "cursor-business-pack-paperwork-included-20260902-01"
        )
        self.assertIs(included["did_not_remint_paperwork_id"], True)
        self.assertEqual(block["id"], "cursor-business-pack-paperwork-20260902-01")
        self.assertEqual(
            self.unique["paperwork"]["included_claim"],
            "cursor-business-pack-paperwork-included-20260902-01",
        )
        self.assertEqual(
            self.law["state_instance"]["id"],
            "cursor-business-pack-paperwork-state-20260902-01",
        )
        self.assertIs(self.law["state_instance"]["did_not_remint_slot_id"], True)
        self.assertTrue(
            (ROOT / "ground" / "BUSINESS_PACK_PAPERWORK_SLOT.json").is_file()
        )
        self.assertTrue(
            (ROOT / "revenue" / "business_packs_marketing" / "PAPERWORK.md").is_file()
        )

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
