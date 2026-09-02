#!/usr/bin/env python3
"""SHIP leftover for the Harborline map pin-lift unique-pack pointer. Does not remint."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_harborline_map_pin_lift_pointer_ship as ship  # noqa: E402

POINTER_ID = "cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01"
LEFTOVER_ID = "cursor-pack-harborline-map-pin-lift-20260902-01"
SHIP_ID = "cursor-business-pack-harborline-map-pin-lift-pointer-ship-20260902-01"
CATALOG_ID = "cursor-business-pack-instance-catalog-20260902-01"
UNIQUE_PACK_ID = "cursor-business-packs-unique-20260902-01"
SOLD_ONCE_PIN_LIFT_ID = "cursor-business-pack-sold-once-badge-pin-lift-20260902-01"
COMPOSE_ID = "cursor-business-pack-harborline-map-pin-lift-compose-20260902-01"
TALLY_SOLD_ONCE_ID = "tally-door-sold-once-badge-20260902-01"
CANDIDATE_SHA = "af2b82f9a16185660e378a4a6f28c78dc827bb6e"
LEFTOVER_BLOB = "8fe8a002"
POINTER_BLOB = "7a8987b5"


class HarborlineMapPinLiftPointerShipTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = ship.load_law()
        self.instances = ship.instances_block(self.law)
        self.result = ship.classify_ship(self.law)
        self.pointer = (ROOT / "p" / f"{POINTER_ID}.md").read_text(encoding="utf-8")
        self.leftover = (ROOT / "p" / f"{LEFTOVER_ID}.md").read_text(encoding="utf-8")
        self.ship = (ROOT / "p" / f"{SHIP_ID}.md").read_text(encoding="utf-8")

    def test_ship_cites_pointer_without_remint(self) -> None:
        self.assertEqual(self.law["id"], UNIQUE_PACK_ID)
        self.assertEqual(self.instances["id"], CATALOG_ID)
        self.assertEqual(self.instances["harborline_map_pin_lift"], LEFTOVER_ID)
        self.assertEqual(self.instances["harborline_map_pin_lift_blob"], LEFTOVER_BLOB)
        self.assertEqual(self.instances["harborline_map_pin_lift_pointer"], POINTER_ID)
        self.assertIs(self.instances["did_not_write_harborline_map_pin_lift"], True)
        self.assertIs(self.instances["did_not_remint_harborline_map_pin_lift"], True)
        self.assertIs(self.instances["harborline_leftover_live_instance_blobs_not_pinned"], True)
        self.assertEqual(self.instances["checkout"], "NOT_MINTED")
        self.assertNotEqual(SHIP_ID, POINTER_ID)
        self.assertNotEqual(SHIP_ID, LEFTOVER_ID)
        self.assertNotEqual(SHIP_ID, CATALOG_ID)
        self.assertNotEqual(SHIP_ID, SOLD_ONCE_PIN_LIFT_ID)
        self.assertNotEqual(SHIP_ID, COMPOSE_ID)
        self.assertIn(f"id: {SHIP_ID}", self.ship)
        self.assertIn(POINTER_ID, self.ship)
        self.assertIn(LEFTOVER_ID, self.ship)
        self.assertIn(CANDIDATE_SHA, self.ship)
        self.assertIn("NOT_MINTED", self.ship)
        self.assertIn("Catalog-only", self.ship)
        self.assertIn(LEFTOVER_BLOB, self.ship)
        self.assertIn(POINTER_BLOB, self.ship)
        self.assertIn("does not freeze TALLY sold-once receipt absence", self.ship)
        self.assertIn("8fe8a002", self.pointer)
        self.assertIn("NOT_MINTED", self.pointer)
        self.assertIn("NOT_MINTED", self.leftover)
        self.assertTrue(ship.blob_prefix(f"p/{POINTER_ID}.md").startswith(POINTER_BLOB))
        self.assertTrue(ship.blob_prefix(f"p/{LEFTOVER_ID}.md").startswith(LEFTOVER_BLOB))
        self.assertTrue((ROOT / "p" / f"{POINTER_ID}.md").is_file())
        self.assertTrue((ROOT / "p" / f"{LEFTOVER_ID}.md").is_file())
        self.assertTrue((ROOT / "p" / f"{COMPOSE_ID}.md").is_file())
        self.assertIn(COMPOSE_ID, self.ship)

    def test_does_not_freeze_tally_sold_once_receipt_absence(self) -> None:
        self.assertTrue(self.result["ship_ok"])
        self.assertTrue(self.result["does_not_freeze_tally_sold_once_absence"])
        self.assertIs(self.result["tally_sold_once_required"], False)
        self.assertIs(self.result["tally_sold_once_forbidden"], False)
        self.assertEqual(self.result["id"], SHIP_ID)
        self.assertEqual(self.result["pointer_id"], POINTER_ID)
        self.assertEqual(self.result["leftover_id"], LEFTOVER_ID)
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertNotIn(f"p/{TALLY_SOLD_ONCE_ID}.md", ship.EXPECTED_BLOBS)
        self.assertNotIn(TALLY_SOLD_ONCE_ID, ship.EXPECTED_BLOBS)
        self.assertNotIn(f"p/{TALLY_SOLD_ONCE_ID}.md", ship.THIS_SEAT_PATHS)
        self.assertNotIn("ground/BUSINESS_PACKS.json", ship.THIS_SEAT_PATHS)
        self.assertNotIn("test_business_pack_unique.py", ship.THIS_SEAT_PATHS)
        self.assertNotIn(f"p/{POINTER_ID}.md", ship.THIS_SEAT_PATHS)
        self.assertNotIn(f"p/{LEFTOVER_ID}.md", ship.THIS_SEAT_PATHS)
        self.assertIn("does not freeze TALLY sold-once receipt absence", self.pointer)
        self.assertIs(self.instances["did_not_write_tally_sold_once_paths"], True)

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_harborline_map_pin_lift_pointer_ship.py"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertTrue(data["ship_ok"])
        self.assertTrue(data["does_not_freeze_tally_sold_once_absence"])
        self.assertEqual(data["id"], SHIP_ID)
        self.assertEqual(data["pointer_id"], POINTER_ID)
        self.assertEqual(data["leftover_id"], LEFTOVER_ID)
        self.assertEqual(data["candidate_sha"], CANDIDATE_SHA)
        self.assertEqual(data["checkout"], "NOT_MINTED")
        self.assertIs(data["tally_sold_once_required"], False)
        self.assertIs(data["tally_sold_once_forbidden"], False)
        self.assertTrue(data["did_not_remint_pointer"])
        self.assertTrue(data["did_not_remint_leftover"])
        self.assertNotIn("337 NO", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
