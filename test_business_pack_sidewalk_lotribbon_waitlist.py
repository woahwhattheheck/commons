#!/usr/bin/env python3
"""Catalog-only waitlist rows for Sidewalk Signal + LotRibbon."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_sidewalk_lotribbon_waitlist as pointer  # noqa: E402


class BusinessPackSidewalkLotribbonWaitlistTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = pointer.load_law()
        self.block = pointer.instance_block(self.law)
        self.card = (ROOT / "ground" / "BUSINESS_PACKS.md").read_text(encoding="utf-8")
        self.door = (ROOT / "business-packs.html").read_text(encoding="utf-8")
        self.receipt = (
            ROOT / "p" / "cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.result = pointer.classify_pointer(self.law)

    def test_pointer_does_not_remint_landed_ids(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(self.block["id"], "cursor-business-pack-instance-catalog-20260902-01")
        self.assertEqual(
            self.law["waitlist"]["id"],
            "cursor-business-pack-waitlist-pointer-20260902-01",
        )
        self.assertEqual(
            self.block["harborline_waitlist_slot_pointer"],
            "cursor-business-pack-harborline-waitlist-slot-pointer-20260902-01",
        )
        self.assertEqual(
            self.block.get("catalog_waitlist_rows_pointer")
            or self.block.get("sidewalk_lotribbon_waitlist_pointer"),
            "cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01",
        )
        self.assertNotEqual(
            self.block["id"],
            self.block.get("catalog_waitlist_rows_pointer")
            or self.block.get("sidewalk_lotribbon_waitlist_pointer"),
        )
        self.assertTrue(self.result["ids_not_reminted"])
        self.assertTrue(self.result["pointer_ok"])
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)

    def test_catalog_rows_point_at_shared_waitlist(self) -> None:
        for brand in ("LotRibbon Greetings", "Sidewalk Signal"):
            row = pointer.landed_row(self.block, brand)
            self.assertEqual(row["waitlist"], "packs/waitlist.html")
            self.assertEqual(self.result["rows"][brand]["waitlist"], "packs/waitlist.html")
            self.assertTrue(self.result["rows"][brand]["points_at_shared_waitlist"])
        harborline = pointer.landed_row(self.block, "Harborline Local Sites")
        self.assertEqual(harborline["waitlist"], "packs/waitlist.html")
        self.assertTrue(self.result["catalog_waitlist_ok"])
        self.assertEqual(self.result["waitlist"], "packs/waitlist.html")
        self.assertTrue((ROOT / "packs" / "waitlist.html").is_file())

    def test_instance_doors_stay_with_owners(self) -> None:
        self.assertTrue(self.result["rows"]["LotRibbon Greetings"]["door_blob"])
        self.assertTrue(self.result["rows"]["Sidewalk Signal"]["door_blob"])
        self.assertTrue(self.result["owner_doors_present"])
        self.assertIs(self.result["live_owner_blobs_not_pinned"], True)
        self.assertEqual(
            self.result["observed_at_land"][
                "packs/lotribbon-greetings-20260902-01/index.html"
            ],
            "ac60db02",
        )
        self.assertEqual(
            self.result["observed_at_land"][
                "packs/sidewalk-signal-web-desk-20260902-01/index.html"
            ],
            "638e60b4",
        )
        self.assertIs(self.block["did_not_overwrite_sidewalk_door"], True)
        self.assertIs(self.block["did_not_overwrite_lotribbon_door"], True)
        self.assertIs(self.block["did_not_overwrite_waitlist_html"], True)
        self.assertIs(self.block["did_not_steal_desk_helper"], True)
        sidewalk = (ROOT / "packs/sidewalk-signal-web-desk-20260902-01/index.html").read_text(
            encoding="utf-8"
        )
        lotribbon = (ROOT / "packs/lotribbon-greetings-20260902-01/index.html").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("packs/waitlist.html", sidewalk)
        self.assertNotIn("packs/waitlist.html", lotribbon)

    def test_checkout_stays_not_minted_and_door_stays_open(self) -> None:
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertIs(self.result["agents_spend_ads"], False)
        self.assertIs(self.result["no_auth"], True)
        self.assertIs(self.result["commons_admission"], False)
        self.assertNotIn("337 NO", json.dumps(self.block))
        self.assertNotIn("337 NO", self.card)
        self.assertNotIn("337 NO", self.door)
        self.assertNotIn("<form", self.door)
        self.assertIn("password", self.door)
        self.assertIn("NOT_MINTED", self.card)
        self.assertIn("NOT_MINTED", self.door)

    def test_card_and_door_name_the_catalog_rows(self) -> None:
        self.assertIn("LotRibbon Greetings", self.card)
        self.assertIn("Sidewalk Signal", self.card)
        self.assertIn("packs/waitlist.html", self.card)
        self.assertIn("638e60b4", self.card)
        self.assertIn("ac60db02", self.card)
        self.assertIn("LotRibbon Greetings", self.door)
        self.assertIn("Sidewalk Signal", self.door)
        self.assertIn('href="./packs/waitlist.html"', self.door)
        self.assertIn("catalog rows", self.door.lower())
        self.assertIn("waitlist", self.door.lower())
        self.assertIn("LotRibbon", self.receipt)
        self.assertIn("Sidewalk Signal", self.receipt)
        self.assertIn("packs/waitlist.html", self.receipt)
        self.assertIn("NOT_MINTED", self.receipt)
        self.assertIn("638e60b4", self.receipt)
        self.assertIn("ac60db02", self.receipt)
        helper_receipt = (
            ROOT / "p" / "cursor-business-pack-sidewalk-lotribbon-waitlist-helper-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.assertIn("not reminted", helper_receipt)
        self.assertIn("2c584983", helper_receipt)

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_sidewalk_lotribbon_waitlist.py"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertIs(data["gate"], False)
        self.assertIs(data["commons_admission"], False)
        self.assertTrue(data["pointer_ok"])
        self.assertTrue(data["catalog_only"])
        self.assertTrue(data["catalog_waitlist_ok"])
        self.assertTrue(data["owner_doors_present"])
        self.assertIs(data["live_owner_blobs_not_pinned"], True)
        self.assertEqual(data["checkout"], "NOT_MINTED")
        self.assertEqual(
            data["id"],
            "cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01",
        )


if __name__ == "__main__":
    unittest.main()
