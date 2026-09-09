#!/usr/bin/env python3
"""SHIP leftover for the Harborline map-helper catalog pointer. Does not remint."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POINTER_ID = "cursor-business-pack-harborline-map-helper-pointer-20260902-01"
SHIP_ID = "cursor-business-pack-harborline-map-helper-pointer-ship-20260902-01"
HELPER_ID = "cursor-business-pack-harborline-tally-map-pointer-helper-20260902-01"
MAP_POINTER_ID = "cursor-business-pack-harborline-tally-map-pointer-20260902-01"
CATALOG_ID = "cursor-business-pack-instance-catalog-20260902-01"
SIDEWALK_LOTRIBBON_ID = "cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01"
CANDIDATE_SHA = "6c1ae9b39f8f6cfd2afd6c54e9baa8a8c42ec3d4"
POINTER_BLOB = "269e874a"
HELPER_BLOB = "5f3d59ba"
KEEP_MAIN_BLOB = "2c584983"


class HarborlineMapHelperPointerShipTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = json.loads((ROOT / "ground" / "BUSINESS_PACKS.json").read_text(encoding="utf-8"))
        self.instances = self.law["instances"]
        self.pointer = (ROOT / "p" / f"{POINTER_ID}.md").read_text(encoding="utf-8")
        self.ship = (ROOT / "p" / f"{SHIP_ID}.md").read_text(encoding="utf-8")
        self.helper = (ROOT / "p" / f"{HELPER_ID}.md").read_text(encoding="utf-8")
        self.keep_main = (ROOT / "p" / f"{SIDEWALK_LOTRIBBON_ID}.md").read_text(encoding="utf-8")

    def test_ship_cites_pointer_without_remint(self) -> None:
        self.assertEqual(self.instances["id"], CATALOG_ID)
        self.assertEqual(
            self.instances["harborline_tally_pack_map_pointer"],
            MAP_POINTER_ID,
        )
        self.assertEqual(
            self.instances["harborline_tally_pack_map_pointer_helper"],
            "host/business_pack_harborline_tally_map_pointer.py",
        )
        self.assertEqual(
            self.instances["harborline_tally_pack_map_pointer_helper_receipt"],
            HELPER_ID,
        )
        self.assertEqual(self.instances["harborline_tally_pack_map_pointer_helper_sha"], "636e2e2fd")
        self.assertIs(self.instances["did_not_write_harborline_tally_map_pointer_helper"], True)
        self.assertEqual(self.instances["catalog_waitlist_rows_pointer"], SIDEWALK_LOTRIBBON_ID)
        self.assertEqual(self.instances["checkout"], "NOT_MINTED")
        self.assertNotEqual(SHIP_ID, POINTER_ID)
        self.assertNotEqual(SHIP_ID, HELPER_ID)
        self.assertNotEqual(SHIP_ID, MAP_POINTER_ID)
        self.assertNotEqual(SHIP_ID, CATALOG_ID)
        self.assertNotEqual(SHIP_ID, SIDEWALK_LOTRIBBON_ID)
        self.assertIn(f"id: {SHIP_ID}", self.ship)
        self.assertIn(POINTER_ID, self.ship)
        self.assertIn(CANDIDATE_SHA, self.ship)
        self.assertIn("NOT_MINTED", self.ship)
        self.assertIn("Catalog-only", self.ship)
        self.assertIn("KEEP MAIN", self.ship)
        self.assertIn("#7754", self.ship)
        self.assertIn(KEEP_MAIN_BLOB, self.ship)
        self.assertIn(POINTER_BLOB, self.ship)
        self.assertIn(HELPER_BLOB, self.ship)
        self.assertIn("not reminted", self.pointer.lower())
        self.assertIn("KEEP MAIN on remint #7754", self.pointer)
        self.assertIn("NOT_MINTED", self.helper)
        self.assertIn("id: " + SIDEWALK_LOTRIBBON_ID, self.keep_main)
        self.assertTrue((ROOT / "host" / "business_pack_harborline_tally_map_pointer.py").is_file())
        self.assertTrue((ROOT / "host" / "harborline_tally_pack_map.py").is_file())
        self.assertTrue((ROOT / "p" / f"{MAP_POINTER_ID}.md").is_file())


if __name__ == "__main__":
    unittest.main()
