#!/usr/bin/env python3
"""Catalog waitlist rows for Sidewalk + LotRibbon. Does not overwrite instance doors."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_instance_waitlist as helper  # noqa: E402


class BusinessPackInstanceWaitlistTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = helper.load_law()
        self.block = helper.instances_block(self.law)
        self.result = helper.classify_catalog(self.law)
        self.door = (ROOT / "business-packs.html").read_text(encoding="utf-8")
        self.card = (ROOT / "ground" / "BUSINESS_PACKS.md").read_text(encoding="utf-8")
        self.receipt = (
            ROOT
            / "p"
            / "cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01.md"
        ).read_text(encoding="utf-8")

    def test_pointer_does_not_remint_catalog_or_unique_pack(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(self.block["id"], "cursor-business-pack-instance-catalog-20260902-01")
        self.assertEqual(
            self.block["catalog_waitlist_rows_pointer"],
            "cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01",
        )
        self.assertEqual(
            self.block["instance_waitlist_helper"],
            "host/business_pack_instance_waitlist.py",
        )
        self.assertNotEqual(self.block["id"], self.block["catalog_waitlist_rows_pointer"])
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertTrue(self.result["pointer_ok"])

    def test_sidewalk_and_lotribbon_are_catalog_pointers_not_door_edits(self) -> None:
        by_brand = {row["brand"]: row for row in self.result["rows"]}
        sidewalk = by_brand["Sidewalk Signal"]
        lotribbon = by_brand["LotRibbon Greetings"]
        harborline = by_brand["Harborline Local Sites"]
        self.assertEqual(sidewalk["waitlist"], "packs/waitlist.html")
        self.assertEqual(lotribbon["waitlist"], "packs/waitlist.html")
        self.assertEqual(harborline["waitlist"], "packs/waitlist.html")
        self.assertEqual(sidewalk["verdict"], helper.WAITLIST_CATALOG_POINTER)
        self.assertEqual(lotribbon["verdict"], helper.WAITLIST_CATALOG_POINTER)
        self.assertEqual(harborline["verdict"], helper.WAITLIST_ON_INSTANCE_DOOR)
        self.assertTrue(sidewalk["door_blob"].startswith("638e60b4"))
        self.assertTrue(lotribbon["door_blob"].startswith("ac60db02"))
        self.assertTrue(harborline["door_blob"].startswith("d3d6fcc7"))
        self.assertIs(self.block["did_not_overwrite_sidewalk_door"], True)
        self.assertIs(self.block["did_not_overwrite_lotribbon_door"], True)
        self.assertIs(self.block["did_not_steal_instance_files"], True)
        self.assertIs(self.block["did_not_overwrite_waitlist_html"], True)
        sidewalk_html = (
            ROOT / "packs" / "sidewalk-signal-web-desk-20260902-01" / "index.html"
        ).read_text(encoding="utf-8")
        lotribbon_html = (
            ROOT / "packs" / "lotribbon-greetings-20260902-01" / "index.html"
        ).read_text(encoding="utf-8")
        harborline_html = (
            ROOT / "packs" / "desk-website-service-20260902-01" / "door.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn("waitlist.html", sidewalk_html.lower())
        self.assertNotIn("waitlist.html", lotribbon_html.lower())
        self.assertIn("waitlist.html", harborline_html.lower())
        self.assertNotIn("<form", self.door)
        self.assertIn("password", self.door)

    def test_peer_blobs_and_helper_stay_put(self) -> None:
        self.assertTrue(self.result["blobs_match"])
        self.assertTrue(self.result["blobs"]["packs/waitlist.html"].startswith("bdcaa7ea"))
        self.assertTrue(
            self.result["blobs"]["host/business_pack_desk_instance.py"].startswith("a550ae1b")
        )
        self.assertEqual(self.block["shared_desk_helper"], "host/business_pack_desk_instance.py")
        self.assertEqual(self.block["checkout"], "NOT_MINTED")
        self.assertNotIn("337 NO", json.dumps(self.block))
        self.assertNotIn("337 NO", self.door)
        self.assertNotIn("337 NO", self.card)

    def test_card_door_receipt_point_without_hosting_the_form(self) -> None:
        self.assertIn("Sidewalk Signal", self.door)
        self.assertIn("LotRibbon Greetings", self.door)
        self.assertIn("packs/waitlist.html", self.door)
        self.assertIn("did not overwrite", self.door.lower())
        self.assertIn("Sidewalk Signal", self.card)
        self.assertIn("LotRibbon", self.card)
        self.assertIn("catalog", self.card.lower())
        self.assertIn("NOT_MINTED", self.receipt)
        self.assertIn("638e60b4", self.receipt)
        self.assertIn("ac60db02", self.receipt)
        self.assertIn("cursor-business-pack-instance-catalog-20260902-01", self.receipt)
        self.assertIn("did not overwrite", self.receipt.lower())

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "business_pack_instance_waitlist.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertIs(data["gate"], False)
        self.assertIs(data["commons_admission"], False)
        self.assertTrue(data["pointer_ok"])
        self.assertEqual(
            data["id"],
            "cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01",
        )
        self.assertEqual(data["checkout"], "NOT_MINTED")


if __name__ == "__main__":
    unittest.main()
