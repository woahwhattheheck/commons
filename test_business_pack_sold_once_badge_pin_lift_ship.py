#!/usr/bin/env python3
"""SHIP leftover for the sold-once badge pin-lift. Does not remint."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_sold_once_badge_pin_lift_ship as ship  # noqa: E402
import business_pack_sold_once_badge_pointer as leftover  # noqa: E402

POINTER_ID = "cursor-business-pack-sold-once-badge-pointer-20260902-01"
HELPER_ID = "cursor-business-pack-sold-once-badge-pointer-helper-20260902-01"
PIN_LIFT_ID = "cursor-business-pack-sold-once-badge-pin-lift-20260902-01"
SHIP_ID = "cursor-business-pack-sold-once-badge-pin-lift-ship-20260902-01"
CATALOG_ID = "cursor-business-pack-instance-catalog-20260902-01"
HARBORLINE_PIN_LIFT = "cursor-pack-harborline-map-pin-lift-20260902-01"
CANDIDATE_SHA = "f080fbbb241a1550b3eb5d94c9041c21cd264d82"
LEFTOVER_BLOB = "da2d1ef5"
POINTER_BLOB = "1cc11a5f"
HELPER_BLOB = "80602a55"


class SoldOnceBadgePinLiftShipTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = ship.load_law()
        self.instances = ship.instances_block(self.law)
        self.result = ship.classify_ship(self.law)
        self.leftover = leftover.classify_pointer(self.law)
        self.pointer = (ROOT / "p" / f"{POINTER_ID}.md").read_text(encoding="utf-8")
        self.pin_lift = (ROOT / "p" / f"{PIN_LIFT_ID}.md").read_text(encoding="utf-8")
        self.ship = (ROOT / "p" / f"{SHIP_ID}.md").read_text(encoding="utf-8")
        self.helper = (ROOT / "p" / f"{HELPER_ID}.md").read_text(encoding="utf-8")

    def test_ship_cites_leftover_without_remint(self) -> None:
        self.assertEqual(self.instances["id"], CATALOG_ID)
        self.assertEqual(self.instances["sold_once_badge_pointer"], POINTER_ID)
        self.assertEqual(self.instances["sold_once_badge_pin_lift"], PIN_LIFT_ID)
        self.assertIs(self.instances["sold_once_badge_live_instance_blobs_not_pinned"], True)
        self.assertIs(self.instances["did_not_remint_sold_once_badge_pointer"], True)
        self.assertIs(self.instances["did_not_write_harborline_leftover_pin_helpers"], True)
        self.assertEqual(self.instances["checkout"], "NOT_MINTED")
        self.assertNotEqual(SHIP_ID, PIN_LIFT_ID)
        self.assertNotEqual(SHIP_ID, POINTER_ID)
        self.assertNotEqual(SHIP_ID, HELPER_ID)
        self.assertNotEqual(SHIP_ID, CATALOG_ID)
        self.assertNotEqual(SHIP_ID, HARBORLINE_PIN_LIFT)
        self.assertIn(f"id: {SHIP_ID}", self.ship)
        self.assertIn(PIN_LIFT_ID, self.ship)
        self.assertIn(CANDIDATE_SHA, self.ship)
        self.assertIn("NOT_MINTED", self.ship)
        self.assertIn("Catalog-only", self.ship)
        self.assertIn(LEFTOVER_BLOB, self.ship)
        self.assertIn(POINTER_BLOB, self.ship)
        self.assertIn(HELPER_BLOB, self.ship)
        self.assertIn("observed_at_land", self.ship)
        self.assertIn("not reminted", self.pin_lift.lower())
        self.assertIn("NOT_MINTED", self.pin_lift)
        self.assertIn("NOT_MINTED", self.helper)
        self.assertTrue(
            leftover.blob_prefix(f"p/{POINTER_ID}.md").startswith(POINTER_BLOB)
        )
        self.assertIn("TALLY", self.pointer)
        self.assertTrue((ROOT / "host" / "business_pack_sold_once_badge_pointer.py").is_file())
        self.assertTrue((ROOT / "p" / f"{PIN_LIFT_ID}.md").is_file())
        self.assertTrue((ROOT / "p" / f"{HARBORLINE_PIN_LIFT}.md").is_file())

    def test_live_sidewalk_and_helper_blobs_stay_observed(self) -> None:
        self.assertTrue(self.result["ship_ok"])
        self.assertTrue(self.result["live_pins_lifted"])
        self.assertIs(self.result["live_instance_blobs_not_pinned"], True)
        self.assertEqual(self.result["id"], SHIP_ID)
        self.assertEqual(self.result["leftover_id"], PIN_LIFT_ID)
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertEqual(
            self.result["observed_at_land"][ship.SIDEWALK_DOOR],
            "638e60b4",
        )
        self.assertEqual(
            self.result["observed_at_land"][ship.TALLY_HELPER],
            "a550ae1b",
        )
        self.assertNotIn(ship.SIDEWALK_DOOR, leftover.EXPECTED_BLOBS)
        self.assertNotIn(ship.TALLY_HELPER, leftover.EXPECTED_BLOBS)
        self.assertEqual(
            leftover.OBSERVED_AT_LAND[ship.SIDEWALK_DOOR],
            "638e60b4",
        )
        self.assertEqual(
            leftover.OBSERVED_AT_LAND[ship.TALLY_HELPER],
            "a550ae1b",
        )
        self.assertIs(self.leftover["live_instance_blobs_not_pinned"], True)
        self.assertNotIn(ship.LEFTOVER_HELPER, ship.THIS_SEAT_PATHS)
        self.assertNotIn(f"p/{PIN_LIFT_ID}.md", ship.THIS_SEAT_PATHS)
        self.assertNotIn("ground/BUSINESS_PACKS.json", ship.THIS_SEAT_PATHS)

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_sold_once_badge_pin_lift_ship.py"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertTrue(data["ship_ok"])
        self.assertTrue(data["live_pins_lifted"])
        self.assertEqual(data["id"], SHIP_ID)
        self.assertEqual(data["leftover_id"], PIN_LIFT_ID)
        self.assertEqual(data["candidate_sha"], CANDIDATE_SHA)
        self.assertEqual(data["checkout"], "NOT_MINTED")
        self.assertIs(data["live_instance_blobs_not_pinned"], True)


if __name__ == "__main__":
    unittest.main()
