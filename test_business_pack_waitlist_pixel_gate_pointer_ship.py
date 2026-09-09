#!/usr/bin/env python3
"""SHIP leftover for the waitlist pixel-gate catalog pointer. Does not remint."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POINTER_ID = "cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01"
SHIP_ID = "cursor-business-pack-waitlist-pixel-gate-pointer-ship-20260902-01"
HELPER_ID = "cursor-business-pack-waitlist-pixel-gate-pointer-helper-20260902-01"
WAITLIST_POINTER_ID = "cursor-business-pack-waitlist-pointer-20260902-01"
PIXEL_GATE_RECEIPT = "cursor-pack-waitlist-pixel-gate-20260902-01"
SCOUT_DEMAND_ID = "scout-demand-pack-door-waitlist-20260902-01"
CANDIDATE_SHA = "00e869034141867ff85d6f646263b980fa792cd0"


class WaitlistPixelGatePointerShipTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = json.loads((ROOT / "ground" / "BUSINESS_PACKS.json").read_text(encoding="utf-8"))
        self.waitlist = self.law["waitlist"]
        self.thanks = self.law["thanks_pixel"]
        self.pointer = (ROOT / "p" / f"{POINTER_ID}.md").read_text(encoding="utf-8")
        self.ship = (ROOT / "p" / f"{SHIP_ID}.md").read_text(encoding="utf-8")
        self.helper = (ROOT / "p" / f"{HELPER_ID}.md").read_text(encoding="utf-8")

    def test_ship_cites_pointer_without_remint(self) -> None:
        self.assertEqual(self.waitlist["id"], WAITLIST_POINTER_ID)
        self.assertEqual(self.waitlist["pixel_gate_pointer"], POINTER_ID)
        self.assertEqual(self.waitlist["pixel_gate_receipt"], PIXEL_GATE_RECEIPT)
        self.assertEqual(self.waitlist["scout_demand_id"], SCOUT_DEMAND_ID)
        self.assertEqual(self.waitlist["checkout"], "NOT_MINTED")
        self.assertEqual(self.thanks["checkout"], "NOT_MINTED")
        self.assertIs(self.waitlist["did_not_write_pixel_gate_paths"], True)
        self.assertIs(self.waitlist["ccpa_opt_out_blocks_thanks_pixels"], True)
        self.assertIs(self.waitlist["empty_slots_load_nothing"], True)
        self.assertNotEqual(SHIP_ID, POINTER_ID)
        self.assertNotEqual(SHIP_ID, HELPER_ID)
        self.assertNotEqual(SHIP_ID, WAITLIST_POINTER_ID)
        self.assertNotEqual(SHIP_ID, PIXEL_GATE_RECEIPT)
        self.assertNotEqual(SHIP_ID, SCOUT_DEMAND_ID)
        self.assertIn(f"id: {SHIP_ID}", self.ship)
        self.assertIn(POINTER_ID, self.ship)
        self.assertIn(CANDIDATE_SHA, self.ship)
        self.assertIn("NOT_MINTED", self.ship)
        self.assertIn("Catalog-only", self.ship)
        self.assertIn("not reminted", self.pointer.lower())
        self.assertIn("NOT_MINTED", self.helper)
        self.assertTrue((ROOT / "host" / "pack_waitlist_pixel_gate.py").is_file())
        self.assertTrue((ROOT / "host" / "pack_waitlist_pixel_gate_pointer.py").is_file())
        self.assertTrue((ROOT / "packs" / "waitlist.html").is_file())
        self.assertTrue((ROOT / "packs" / "thanks.html").is_file())


if __name__ == "__main__":
    unittest.main()
