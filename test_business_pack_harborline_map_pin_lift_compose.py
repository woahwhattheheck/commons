#!/usr/bin/env python3
"""Leftover helper for the Harborline map pin-lift compose. Does not remint."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_harborline_map_pin_lift_compose as compose  # noqa: E402

COMPOSE_ID = "cursor-business-pack-harborline-map-pin-lift-compose-20260902-01"
SHIP_ID = "cursor-business-pack-harborline-map-pin-lift-compose-ship-20260902-01"
HELPER_ID = "cursor-business-pack-harborline-map-pin-lift-compose-helper-20260902-01"
POINTER_ID = "cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01"
LEFTOVER_ID = "cursor-pack-harborline-map-pin-lift-20260902-01"
POINTER_SHIP_ID = "cursor-business-pack-harborline-map-pin-lift-pointer-ship-20260902-01"
SOLD_ONCE_PIN_LIFT_ID = "cursor-business-pack-sold-once-badge-pin-lift-20260902-01"
CATALOG_ID = "cursor-business-pack-instance-catalog-20260902-01"
UNIQUE_PACK_ID = "cursor-business-packs-unique-20260902-01"
LAND_FILE = "land/pack-harborline-map-pin-lift-pointer-20260902.md"
CANDIDATE_SHA = "7d6a4df1be98b213b98f3d9b81de7bd7c08b7fa5"
COMPOSE_BLOB = "4135cf8f"
SHIP_BLOB = "c449e49f"
POINTER_BLOB = "7a8987b5"
LEFTOVER_BLOB = "8fe8a002"
LAND_BLOB = "fe01649e"
SQUASH = "b9e6f54c"
CLAIMED_BY = "bc-31c8ef9a"


class HarborlineMapPinLiftComposeHelperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = compose.load_law()
        self.instances = compose.instances_block(self.law)
        self.result = compose.classify_compose(self.law)
        self.compose = (ROOT / "p" / f"{COMPOSE_ID}.md").read_text(encoding="utf-8")
        self.ship = (ROOT / "p" / f"{SHIP_ID}.md").read_text(encoding="utf-8")
        self.helper = (ROOT / "p" / f"{HELPER_ID}.md").read_text(encoding="utf-8")
        self.pointer = (ROOT / "p" / f"{POINTER_ID}.md").read_text(encoding="utf-8")
        self.land = (ROOT / LAND_FILE).read_text(encoding="utf-8")

    def test_helper_cites_compose_without_remint(self) -> None:
        self.assertEqual(self.law["id"], UNIQUE_PACK_ID)
        self.assertEqual(self.instances["id"], CATALOG_ID)
        self.assertEqual(self.instances["harborline_map_pin_lift"], LEFTOVER_ID)
        self.assertEqual(self.instances["harborline_map_pin_lift_blob"], LEFTOVER_BLOB)
        self.assertEqual(self.instances["harborline_map_pin_lift_squash"], SQUASH)
        self.assertEqual(self.instances["harborline_map_pin_lift_claimed_by"], CLAIMED_BY)
        self.assertEqual(self.instances["harborline_map_pin_lift_pointer"], POINTER_ID)
        self.assertIs(self.instances["did_not_write_harborline_map_pin_lift"], True)
        self.assertIs(self.instances["did_not_remint_harborline_map_pin_lift"], True)
        self.assertIs(self.instances["did_not_remint_sold_once_badge_pin_lift"], True)
        self.assertIs(self.instances["harborline_leftover_live_instance_blobs_not_pinned"], True)
        self.assertEqual(self.instances["checkout"], "NOT_MINTED")
        self.assertNotEqual(HELPER_ID, COMPOSE_ID)
        self.assertNotEqual(HELPER_ID, SHIP_ID)
        self.assertNotEqual(HELPER_ID, POINTER_ID)
        self.assertNotEqual(HELPER_ID, LEFTOVER_ID)
        self.assertNotEqual(HELPER_ID, POINTER_SHIP_ID)
        self.assertNotEqual(HELPER_ID, SOLD_ONCE_PIN_LIFT_ID)
        self.assertNotEqual(HELPER_ID, CATALOG_ID)
        self.assertIn(f"id: {HELPER_ID}", self.helper)
        self.assertIn(COMPOSE_ID, self.helper)
        self.assertIn(SHIP_ID, self.helper)
        self.assertIn(CANDIDATE_SHA, self.helper)
        self.assertIn("KEEP MAIN", self.helper)
        self.assertIn("#7915", self.helper)
        self.assertIn(POINTER_BLOB, self.helper)
        self.assertIn(SQUASH, self.helper)
        self.assertIn(CLAIMED_BY, self.helper)
        self.assertIn(LAND_FILE, self.helper)
        self.assertIn("NOT_MINTED", self.helper)
        self.assertIn("KEEP MAIN", self.ship)
        self.assertIn(POINTER_BLOB, self.ship)
        self.assertIn("Did not merge #7915", self.compose)
        self.assertIn("KEEP MAIN", self.compose)
        self.assertIn(POINTER_BLOB, self.compose)
        self.assertIn(POINTER_BLOB, self.land)
        self.assertIn("KEEP MAIN", self.land)
        self.assertTrue(compose.blob_prefix(f"p/{COMPOSE_ID}.md").startswith(COMPOSE_BLOB))
        self.assertTrue(compose.blob_prefix(f"p/{SHIP_ID}.md").startswith(SHIP_BLOB))
        self.assertTrue(compose.blob_prefix(f"p/{POINTER_ID}.md").startswith(POINTER_BLOB))
        self.assertTrue(compose.blob_prefix(f"p/{LEFTOVER_ID}.md").startswith(LEFTOVER_BLOB))
        self.assertTrue(compose.blob_prefix(LAND_FILE).startswith(LAND_BLOB))
        self.assertTrue((ROOT / "p" / f"{COMPOSE_ID}.md").is_file())
        self.assertTrue((ROOT / "p" / f"{SHIP_ID}.md").is_file())
        self.assertTrue((ROOT / "p" / f"{POINTER_ID}.md").is_file())
        self.assertTrue((ROOT / LAND_FILE).is_file())
        self.assertIn("no longer freeze TALLY sold-once receipt absence", self.pointer)

    def test_keep_main_pointer_and_harvested_keys(self) -> None:
        self.assertTrue(self.result["compose_ok"])
        self.assertTrue(self.result["keep_main"])
        self.assertTrue(self.result["did_not_remint_compose"])
        self.assertTrue(self.result["did_not_remint_compose_ship"])
        self.assertTrue(self.result["did_not_remint_pointer"])
        self.assertTrue(self.result["did_not_remint_leftover"])
        self.assertTrue(self.result["did_not_merge_7915"])
        self.assertEqual(self.result["id"], HELPER_ID)
        self.assertEqual(self.result["compose_id"], COMPOSE_ID)
        self.assertEqual(self.result["ship_id"], SHIP_ID)
        self.assertEqual(self.result["pointer_id"], POINTER_ID)
        self.assertEqual(self.result["harborline_map_pin_lift_squash"], SQUASH)
        self.assertEqual(self.result["harborline_map_pin_lift_claimed_by"], CLAIMED_BY)
        self.assertEqual(self.result["land_file"], LAND_FILE)
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertEqual(self.result["keep_main_pr"], 7915)
        self.assertNotIn(f"p/{COMPOSE_ID}.md", compose.THIS_SEAT_PATHS)
        self.assertNotIn(f"p/{SHIP_ID}.md", compose.THIS_SEAT_PATHS)
        self.assertNotIn(f"p/{POINTER_ID}.md", compose.THIS_SEAT_PATHS)
        self.assertNotIn(LAND_FILE, compose.THIS_SEAT_PATHS)
        self.assertNotIn("ground/BUSINESS_PACKS.json", compose.THIS_SEAT_PATHS)
        self.assertNotIn("test_business_pack_unique.py", compose.THIS_SEAT_PATHS)
        self.assertTrue(self.result["live_instance_blobs_not_pinned"])

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_harborline_map_pin_lift_compose.py"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertTrue(data["compose_ok"])
        self.assertTrue(data["keep_main"])
        self.assertEqual(data["id"], HELPER_ID)
        self.assertEqual(data["compose_id"], COMPOSE_ID)
        self.assertEqual(data["ship_id"], SHIP_ID)
        self.assertEqual(data["pointer_id"], POINTER_ID)
        self.assertEqual(data["candidate_sha"], CANDIDATE_SHA)
        self.assertEqual(data["harborline_map_pin_lift_squash"], SQUASH)
        self.assertEqual(data["harborline_map_pin_lift_claimed_by"], CLAIMED_BY)
        self.assertEqual(data["checkout"], "NOT_MINTED")
        self.assertTrue(data["did_not_remint_compose"])
        self.assertTrue(data["did_not_remint_compose_ship"])
        self.assertTrue(data["did_not_remint_pointer"])
        self.assertTrue(data["did_not_merge_7915"])
        self.assertNotIn("337 NO", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
