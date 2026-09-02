#!/usr/bin/env python3
"""Empty pack rating slot: completeness audit, not a dollar valuation."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_rating as rating  # noqa: E402


class BusinessPackRatingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = rating.load_law()
        self.card = (ROOT / "ground" / "BUSINESS_PACK_RATING.md").read_text(
            encoding="utf-8"
        )
        self.sheet = (ROOT / "packs" / "_template" / "rating.md").read_text(
            encoding="utf-8"
        )
        self.door = (ROOT / "business-packs.html").read_text(encoding="utf-8")
        self.unique = json.loads(
            (ROOT / "ground" / "BUSINESS_PACKS.json").read_text(encoding="utf-8")
        )

    def test_law_is_empty_owner_paste_not_a_gate(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-pack-rating-slot-20260902-01")
        self.assertEqual(self.unique["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(self.law["badge_url"], "")
        self.assertEqual(self.law["report_url"], "")
        self.assertEqual(self.law["partner_name"], "OWNER_UNSET")
        self.assertEqual(self.law["bulk_price"], "OWNER_UNSET")
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertIs(self.law["agents_pick_partner"], False)
        self.assertIs(self.law["agents_invent_bulk_price"], False)
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        self.assertIs(self.law["did_not_write_scout_advertising_general"], True)
        self.assertNotIn("337 NO", json.dumps(self.law))
        self.assertNotIn("337 NO", self.card)
        self.assertNotIn("337 NO", self.sheet)

    def test_empty_slot_is_ok(self) -> None:
        result = rating.classify_rating()
        self.assertEqual(result["verdict"], "RATING_SLOT_EMPTY")
        self.assertTrue(result["empty"])
        self.assertFalse(result["filled"])
        self.assertIs(result["gate"], False)
        self.assertEqual(result["checkout"], "NOT_MINTED")

    def test_invented_url_without_owner_paste(self) -> None:
        result = rating.classify_rating(
            {"badge_url": "https://example.invalid/seal.png", "report_url": ""}
        )
        self.assertEqual(result["verdict"], "RATING_LINK_INVENTED")

    def test_dollar_valuation_is_earnings(self) -> None:
        result = rating.classify_rating(
            {
                "copy": "valued at $48,000 by our partner",
                "owner_pasted_rating": True,
                "badge_url": "https://owner.example/seal.png",
                "report_url": "https://owner.example/report.pdf",
            }
        )
        self.assertEqual(result["verdict"], "RATING_EARNINGS_CLAIM")

    def test_independently_audited_needs_filled_slot(self) -> None:
        result = rating.classify_rating({"copy": "Independently audited for completeness."})
        self.assertEqual(result["verdict"], "RATING_CLAIM_UNSUBSTANTIATED")

    def test_owner_filled_completeness_audit(self) -> None:
        result = rating.classify_rating(
            {
                "badge_url": "https://owner.example/seal.png",
                "report_url": "https://owner.example/report.pdf",
                "owner_pasted_rating": True,
                "copy": "completeness checklist linked from the door",
            }
        )
        self.assertEqual(result["verdict"], "RATING_SLOT_OWNER_FILLED")
        self.assertTrue(result["filled"])

    def test_sheet_and_door_stay_open(self) -> None:
        for needle in (
            "Do X",
            "OWNER_UNSET",
            "not a Commons seat",
            "Independently audited",
            "dollar valuation",
            "completeness",
        ):
            self.assertIn(needle, self.sheet)
        self.assertIn("password", self.door)
        self.assertNotIn("<form", self.door)
        self.assertIn("rating", self.door.lower())
        self.assertEqual(
            self.unique["rating_slot"]["id"],
            "cursor-business-pack-rating-slot-20260902-01",
        )
        self.assertIs(
            self.unique["rating_slot"]["did_not_write_scout_advertising_general"],
            True,
        )
        self.assertTrue(
            (ROOT / "p" / "cursor-business-pack-rating-slot-20260902-01.md").is_file()
        )
        self.assertFalse(
            (ROOT / "revenue" / "business_packs_marketing" / "ADVERTISING_GENERAL.md")
            .read_text(encoding="utf-8")
            .startswith("# overwritten")
        )

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "business_pack_rating.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["verdict"], "RATING_SLOT_EMPTY")
        self.assertIs(data["gate"], False)


if __name__ == "__main__":
    unittest.main()
