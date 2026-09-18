#!/usr/bin/env python3
"""Filled factory Do X checklist. Not filing. Not a Commons gate."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_paperwork_included as included  # noqa: E402


EMPTY_SHEET = """# empty

## Registration / DBA

1. Do X:
Status: `OWNER_UNSET`

## EIN

1. Do X:
Status: `OWNER_UNSET`

## Sales tax permit

1. Do X:
Status: `OWNER_UNSET`

## Local business license

1. Do X:
Status: `OWNER_UNSET`

## Insurance

1. Do X:
Status: `OWNER_UNSET`

## Contract

1. Do X:
Status: `OWNER_UNSET`
"""

FILING_SHEET = """# bad

## Registration / DBA

1. Do X: we filed your LLC
Status: `OWNER_UNSET`

## EIN

1. Do X: IRS EIN assistant
Status: `OWNER_UNSET`

## Sales tax permit

1. Do X: revenue portal
Status: `OWNER_UNSET`

## Local business license

1. Do X: city license page
Status: `OWNER_UNSET`

## Insurance

1. Do X: owner-review GL
Status: `OWNER_UNSET`

## Contract

1. Do X: instance template
Status: `OWNER_UNSET`
"""


class BusinessPackPaperworkIncludedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = included.load_law()
        self.card = (ROOT / "ground" / "BUSINESS_PACK_PAPERWORK_INCLUDED.md").read_text(
            encoding="utf-8"
        )
        self.sheet = (ROOT / "packs" / "_template" / "paperwork.md").read_text(
            encoding="utf-8"
        )
        self.factory = json.loads(
            (ROOT / "ground" / "BUSINESS_PACK_PAPERWORK.json").read_text(encoding="utf-8")
        )

    def test_law_is_not_a_commons_gate(self) -> None:
        self.assertEqual(
            self.law["id"], "cursor-business-pack-paperwork-included-20260902-01"
        )
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertEqual(self.law["source_slack_ts"], "1788328090.862799")
        self.assertEqual(self.law["substantiation"], "filled_checklist")
        self.assertEqual(
            self.law["upl_line"], "checklists_links_templates_not_filing"
        )
        self.assertIs(self.law["did_not_remint_paperwork_id"], True)
        self.assertIs(self.law["did_not_write_state_claim"], True)
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        dumped = json.dumps(self.law)
        self.assertNotIn("337 NO", dumped)
        self.assertNotIn("337 NO", self.card)
        self.assertNotIn("buy.stripe.com", self.sheet.lower())

    def test_factory_sheet_homework_is_filled(self) -> None:
        result = included.classify_homework(self.sheet)
        self.assertEqual(result["verdict"], "PAPERWORK_OK")
        self.assertEqual(result["missing"], [])
        self.assertTrue(result["homework_filled"])
        self.assertFalse(result["filing_as_lawyer"])
        self.assertIs(result["gate"], False)
        self.assertIn("irs.gov/ein", result["steps"]["ein"].lower())
        self.assertIn("sba.gov", result["steps"]["registration"].lower())
        self.assertIn("sba.gov", result["steps"]["sales_tax"].lower())
        self.assertIn("sba.gov", result["steps"]["license"].lower())
        self.assertIn("OWNER_UNSET", self.sheet)
        self.assertIn("not tjlabs doing the filing", self.sheet.lower())

    def test_empty_do_x_is_unsubstantiated(self) -> None:
        result = included.classify_homework(EMPTY_SHEET)
        self.assertEqual(result["verdict"], "PAPERWORK_CLAIM_UNSUBSTANTIATED")
        self.assertEqual(set(result["missing"]), set(included.REQUIRED))
        self.assertFalse(result["homework_filled"])
        self.assertIs(result["commons_admission"], False)

    def test_filing_as_lawyer_on_sheet_is_flagged(self) -> None:
        result = included.classify_homework(FILING_SHEET)
        self.assertEqual(result["verdict"], "PAPERWORK_FILING_CLAIM")
        self.assertTrue(result["filing_as_lawyer"])
        self.assertIs(result["legal_advice"], False)

    def test_does_not_remint_factory_id(self) -> None:
        self.assertEqual(
            self.factory["id"], "cursor-business-pack-paperwork-20260902-01"
        )
        self.assertEqual(
            self.factory["included_claim"]["id"],
            "cursor-business-pack-paperwork-included-20260902-01",
        )
        self.assertEqual(
            self.factory["included_claim"]["homework_helper"],
            "host/business_pack_paperwork_included.py",
        )
        self.assertNotIn("MESSAGING_ANGLE.md", json.dumps(self.law))
        self.assertNotIn("PAPERWORK_STATE", json.dumps(self.law))

    def test_cli(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_paperwork_included.py"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "PAPERWORK_OK")
        self.assertEqual(
            payload["law_id"], "cursor-business-pack-paperwork-included-20260902-01"
        )
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".md", delete=False
        ) as handle:
            handle.write(EMPTY_SHEET)
            empty_path = handle.name
        try:
            empty = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "host" / "business_pack_paperwork_included.py"),
                    "--sheet",
                    empty_path,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        finally:
            Path(empty_path).unlink(missing_ok=True)
        empty_payload = json.loads(empty.stdout)
        self.assertEqual(empty_payload["verdict"], "PAPERWORK_CLAIM_UNSUBSTANTIATED")


if __name__ == "__main__":
    unittest.main()
