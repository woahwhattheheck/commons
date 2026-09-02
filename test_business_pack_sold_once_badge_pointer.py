#!/usr/bin/env python3
"""Leftover helper: landed sold-once catalog pointer; LEAD LotRibbon sidecar."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_sold_once_badge_pointer as pointer  # noqa: E402


class BusinessPackSoldOnceBadgePointerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = pointer.load_law()
        self.catalog = pointer.instances_block(self.law)
        self.result = pointer.classify_pointer(self.law)
        self.helper_receipt = (
            ROOT
            / "p"
            / "cursor-business-pack-sold-once-badge-pointer-helper-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.pointer_receipt = (
            ROOT / "p" / "cursor-business-pack-sold-once-badge-pointer-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.peer_plant = (
            ROOT / "p" / "cursor-plant-sold-once-badge-20260902-01.md"
        ).read_text(encoding="utf-8")

    def test_cites_landed_pointer_and_leads_sidecar(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(
            self.catalog["sold_once_badge_pointer"],
            "cursor-business-pack-sold-once-badge-pointer-20260902-01",
        )
        self.assertEqual(self.catalog["sold_once_claimed_by"], "TALLY")
        self.assertEqual(self.result["id"], pointer.HELPER_ID)
        self.assertEqual(self.result["pointer_id"], pointer.POINTER_ID)
        self.assertEqual(self.result["lead_brand"], "LotRibbon Greetings")
        self.assertEqual(self.result["desk_sold_once_cleared_to"], "TALLY")
        self.assertTrue(self.result["pointer_ok"])
        self.assertTrue(self.result["did_not_remint_catalog_pointer"])
        self.assertTrue(self.result["did_not_remint_peer_plant_sold_once"])
        self.assertTrue(self.result["did_not_overwrite_tally_helper"])
        self.assertTrue(self.result["did_not_overwrite_instance_doors"])
        self.assertTrue(self.result["did_not_take_goat_creative_brief"])
        self.assertTrue(self.result["did_not_overwrite_peer_creative_brief"])
        self.assertTrue(self.result["lotribbon_sold_once_present"])
        self.assertTrue(self.result["lotribbon_creative_brief_present"])
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertIs(self.law["gate"], False)

    def test_does_not_steal_or_remint(self) -> None:
        self.assertNotIn("host/business_pack_desk_instance.py", pointer.THIS_SEAT_PATHS)
        self.assertNotIn("host/business_pack_plant_instance.py", pointer.THIS_SEAT_PATHS)
        self.assertNotIn(
            "p/cursor-business-pack-sold-once-badge-pointer-20260902-01.md",
            pointer.THIS_SEAT_PATHS,
        )
        self.assertNotIn(
            "p/cursor-plant-sold-once-badge-20260902-01.md",
            pointer.THIS_SEAT_PATHS,
        )
        self.assertNotIn(
            "packs/lotribbon-greetings-20260902-01/creative_brief.md",
            pointer.THIS_SEAT_PATHS,
        )
        self.assertTrue((ROOT / "packs" / "_template" / "creative_brief.md").is_file())
        self.assertTrue(
            pointer.blob_prefix("packs/_template/creative_brief.md").startswith("f2953322")
        )
        self.assertTrue(
            pointer.blob_prefix(
                "packs/lotribbon-greetings-20260902-01/creative_brief.md"
            ).startswith("4f4cbb7a")
        )
        self.assertTrue(
            pointer.blob_prefix(
                "p/cursor-plant-sold-once-badge-20260902-01.md"
            ).startswith("39d83580")
        )
        self.assertTrue(
            (ROOT / "packs" / "lotribbon-greetings-20260902-01" / "sold-once.md").is_file()
        )
        self.assertIn("1cc11a5f", self.helper_receipt)
        self.assertIn("39d83580", self.helper_receipt)
        self.assertIn("4f4cbb7a", self.helper_receipt)
        self.assertIn("TALLY", self.pointer_receipt)
        self.assertIn("bc-23891c63", self.peer_plant)
        self.assertIn("NOT_MINTED", self.helper_receipt)
        self.assertNotIn("337 NO", self.helper_receipt)

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "business_pack_sold_once_badge_pointer.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertTrue(data["pointer_ok"])
        self.assertEqual(data["id"], pointer.HELPER_ID)
        self.assertEqual(data["pointer_id"], pointer.POINTER_ID)
        self.assertEqual(data["checkout"], "NOT_MINTED")


if __name__ == "__main__":
    unittest.main()
