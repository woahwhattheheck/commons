#!/usr/bin/env python3
"""Filled paperwork-included checklists. Not legal advice. Not a Commons gate."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_paperwork_filled as filled  # noqa: E402
import business_pack_unique as unique  # noqa: E402


SHEET_DIR = ROOT / "packs" / "paperwork-included-20260902-01"
FORBIDDEN = (
    "we handle your legal paperwork",
    "we set up your llc",
    "compliance guaranteed",
    "we filed your llc",
)


class BusinessPackPaperworkFilledTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = filled.load_law()
        self.card = (ROOT / "ground" / "BUSINESS_PACK_PAPERWORK_FILLED.md").read_text(
            encoding="utf-8"
        )
        self.harbor_md = (SHEET_DIR / "harborline-desk.md").read_text(encoding="utf-8")
        self.pier_md = (SHEET_DIR / "pierlight-desk.md").read_text(encoding="utf-8")
        self.harbor = filled.load_instance(SHEET_DIR / "harborline-desk.json")
        self.pier = filled.load_instance(SHEET_DIR / "pierlight-desk.json")
        self.included = (
            ROOT / "p" / "cursor-business-pack-paperwork-included-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.tally = (ROOT / "host" / "desk_website_service_pack.py").read_text(
            encoding="utf-8"
        )
        self.scout = (
            ROOT / "revenue" / "business_packs_marketing" / "PAPERWORK.md"
        ).read_text(encoding="utf-8")

    def test_law_points_at_included_claim_and_is_not_a_gate(self) -> None:
        self.assertEqual(
            self.law["id"], "cursor-business-pack-paperwork-filled-20260902-01"
        )
        self.assertEqual(
            self.law["included_claim_id"],
            "cursor-business-pack-paperwork-included-20260902-01",
        )
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertIs(self.law["did_not_remint_included_claim"], True)
        self.assertIs(self.law["did_not_write_scout_research"], True)
        self.assertIs(self.law["did_not_write_tally_helper"], True)
        self.assertIs(self.law["did_not_write_harborline_instance"], True)
        self.assertIs(self.law["similar_is_not_clone"], True)
        self.assertEqual(self.law["formation_partner"], "OWNER_UNSET")
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        dumped = json.dumps(self.law)
        self.assertNotIn("337 NO", dumped)
        self.assertNotIn("337 NO", self.card)
        self.assertNotIn("buy.stripe.com", self.harbor_md.lower())
        self.assertNotIn("buy.stripe.com", self.pier_md.lower())

    def test_did_not_remint_included_receipt_or_take_peer_files(self) -> None:
        self.assertIn("id: cursor-business-pack-paperwork-included-20260902-01", self.included)
        self.assertNotIn("cursor-business-pack-paperwork-filled", self.tally)
        self.assertNotIn("pierlight-desk", self.tally)
        self.assertNotIn("cursor-business-pack-paperwork-filled", self.scout)

    def test_sheets_parse_to_included_ok(self) -> None:
        for name in ("harborline-desk.md", "pierlight-desk.md"):
            parsed = filled.parse_sheet((SHEET_DIR / name).read_text(encoding="utf-8"))
            parsed.setdefault("copy", "paperwork included")
            result = filled.classify_filled(parsed)
            self.assertEqual(result["verdict"], "PAPERWORK_OK", name)
            self.assertEqual(result["missing"], [])
            self.assertTrue(parsed.get("state"), name)
            self.assertTrue(result["paperwork_included"], name)
            self.assertTrue(result["included_claim"], name)
            self.assertFalse(result["claim_unsubstantiated"], name)
            self.assertIs(result["hold_counsel"], True)

    def test_instances_are_filled_and_similar_not_clone(self) -> None:
        pair = filled.classify_desk_pair()
        self.assertTrue(pair["both_included"])
        self.assertTrue(pair["shared_vertical"])
        self.assertTrue(pair["shared_template"])
        self.assertTrue(pair["similar_is_not_clone"])
        self.assertFalse(pair["clone_stamp"])
        self.assertEqual(pair["sales"]["unique_count"], 2)
        self.assertEqual(
            {row["sale_id"] for row in pair["sales"]["sales"]},
            {
                "desk-website-service-20260902-01-harborline",
                "desk-website-service-20260902-02-pierlight",
            },
        )
        for row in pair["sales"]["sales"]:
            self.assertEqual(row["verdict"], "UNIQUE")
            self.assertEqual(row["template_id"], "desk-website-service")
            self.assertEqual(row["vertical"], "local_website_service")
        self.assertNotEqual(self.harbor["brand"], self.pier["brand"])
        self.assertNotEqual(self.harbor["checkout"], self.pier["checkout"])
        self.assertNotEqual(self.harbor["assets"], self.pier["assets"])
        self.assertNotEqual(self.harbor["instructions"], self.pier["instructions"])
        self.assertNotEqual(
            unique.content_fingerprint(self.harbor),
            unique.content_fingerprint(self.pier),
        )

    def test_clone_stamp_when_pierlight_reuses_harborline_fingerprint(self) -> None:
        clone = dict(self.pier)
        for key in ("assets", "brand", "checkout", "instructions", "ops"):
            clone[key] = self.harbor[key]
        result = unique.classify_sales([self.harbor, clone])
        self.assertTrue(result["clone_stamp"])

    def test_empty_sheet_keeps_included_claim_unsubstantiated(self) -> None:
        result = filled.classify_filled({"copy": "paperwork included"})
        self.assertEqual(result["verdict"], "PAPERWORK_CLAIM_UNSUBSTANTIATED")
        self.assertFalse(result["paperwork_included"])

    def test_forbidden_door_copy_is_absent(self) -> None:
        blob = (self.harbor_md + "\n" + self.pier_md + "\n" + self.card).lower()
        for phrase in FORBIDDEN:
            self.assertNotIn(phrase, blob)
        self.assertIn("irs.gov/ein", self.harbor_md)
        self.assertIn("OWNER_UNSET", self.harbor_md)
        self.assertIn("HOW_TO_FILLED", self.harbor_md)
        self.assertIn("HOW_TO_FILLED", self.pier_md)

    def test_cli_desk_pair(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_paperwork_filled.py"),
                "--desk-pair",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["both_included"])
        self.assertFalse(payload["clone_stamp"])
        self.assertEqual(payload["sales"]["unique_count"], 2)


if __name__ == "__main__":
    unittest.main()
