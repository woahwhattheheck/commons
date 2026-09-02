#!/usr/bin/env python3
"""Harborline waitlist-slot leftover. Does not steal GOAT template or peer packs."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_harborline_waitlist_slot as slot  # noqa: E402


INVENTED = """# Waitlist slot — Harborline Local Sites
id: cursor-pack-door-waitlist-20260902-01
scout-demand-pack-door-waitlist-20260902-01
cursor-business-pack-harborline-waitlist-slot-pointer-20260902-01
Form: packs/waitlist.html
Do Not Sell or Share My Personal Information
Zero sends. not a second list
Checkout stays `NOT_MINTED`.
Did not invent a Harborline manifest.json.
Contact: owner@example.com
"""


class PackHarborlineWaitlistSlotTest(unittest.TestCase):
    def test_does_not_claim_peer_or_factory_paths(self) -> None:
        self.assertIn("packs/_template/waitlist-slot.md", slot.DO_NOT_OVERWRITE)
        self.assertIn("packs/waitlist.html", slot.DO_NOT_OVERWRITE)
        self.assertIn("host/pack_waitlist.py", slot.DO_NOT_OVERWRITE)
        self.assertIn(
            "p/cursor-business-pack-harborline-waitlist-slot-pointer-20260902-01.md",
            slot.DO_NOT_OVERWRITE,
        )
        self.assertIn("packs/desk-website-service-20260902-01/door.html", slot.DO_NOT_OVERWRITE)
        self.assertIn("packs/desk-website-service-20260902-01/rating.md", slot.DO_NOT_OVERWRITE)
        self.assertIn("host/business_pack_harborline_tally_map.py", slot.DO_NOT_OVERWRITE)
        self.assertIn("host/business_pack_harborline_desk_instance.py", slot.DO_NOT_OVERWRITE)
        self.assertIn("packs/sidewalk-signal-web-desk-20260902-01", slot.DO_NOT_OVERWRITE)
        self.assertIn("packs/lotribbon-greetings-20260902-01", slot.DO_NOT_OVERWRITE)
        self.assertIn("packs/curbline-weekend-yard-help-20260902-01", slot.DO_NOT_OVERWRITE)
        self.assertIn("ground/BUSINESS_PACKS.json", slot.DO_NOT_OVERWRITE)
        self.assertIn("packs/desk-website-service-20260902-01/manifest.json", slot.DO_NOT_OVERWRITE)

    def test_harborline_instance_points_at_shared_door(self) -> None:
        if not slot.HARBORLINE.is_file():
            self.skipTest("Harborline waitlist-slot sheet not in this tree")
        result = slot.classify_path(slot.HARBORLINE)
        text = slot.HARBORLINE.read_text(encoding="utf-8")
        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_INSTANCE_OK")
        self.assertIn("Harborline Local Sites", text)
        self.assertIn("packs/waitlist.html", text)
        self.assertIn("cursor-pack-door-waitlist-20260902-01", text)
        self.assertIn("scout-demand-pack-door-waitlist-20260902-01", text)
        self.assertIn("cursor-business-pack-harborline-waitlist-slot-pointer-20260902-01", text)
        self.assertIn("Do Not Sell or Share My Personal Information", text)
        self.assertIn("NOT_MINTED", text)
        self.assertIn("Zero sends", text)
        self.assertNotIn("buy.stripe.com", text.lower())
        self.assertNotIn("@", text)
        self.assertEqual(result["sends"], 0)

    def test_address_leak_fails(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(INVENTED)
            path = Path(handle.name)
        result = slot.classify_path(path)
        path.unlink(missing_ok=True)
        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_INCOMPLETE")
        self.assertIn("address_leak", result["problems"])

    def test_tree_ok_and_leftovers_unread(self) -> None:
        if not slot.TEMPLATE.is_file() or not slot.HARBORLINE.is_file():
            self.skipTest("waitlist-slot files not in this tree")
        result = slot.classify_tree()
        self.assertEqual(result["verdict"], "HARBORLINE_WAITLIST_SLOT_OK", msg=result)
        self.assertTrue(result["did_not_rewrite_goat_template"])
        self.assertTrue(result["did_not_remint_waitlist_door"])
        self.assertTrue(result["did_not_remint_waitlist_helper"])
        self.assertTrue(result["did_not_overwrite_harborline_door"])
        self.assertTrue(result["did_not_overwrite_harborline_rating"])
        self.assertTrue(result["did_not_write_leftover_pin_helpers"])
        self.assertTrue(result["did_not_overwrite_pointer_receipt"])
        self.assertTrue(result["did_not_remint_slot_catalog_pointer"])
        self.assertTrue(result["did_not_fill_sidewalk"])
        self.assertTrue(result["did_not_fill_lotribbon"])
        self.assertTrue(result["did_not_fill_yard"])
        self.assertTrue(result["did_not_invent_harborline_manifest"])
        self.assertTrue(result["did_not_merge_7915"])
        self.assertTrue(result["copy_ok"])
        self.assertEqual(result["blobs"]["packs/_template/waitlist-slot.md"], "50602561")
        self.assertEqual(result["blobs"]["packs/waitlist.html"], "bdcaa7ea")
        self.assertEqual(
            result["blobs"]["packs/desk-website-service-20260902-01/door.html"],
            "d3d6fcc7",
        )
        self.assertEqual(
            result["blobs"]["packs/desk-website-service-20260902-01/rating.md"],
            "7fe8667a",
        )
        self.assertEqual(
            result["blobs"]["host/business_pack_harborline_tally_map.py"],
            "c72d50d0",
        )
        self.assertEqual(
            result["blobs"][
                "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md"
            ],
            "7a8987b5",
        )
        dumped = json.dumps(result)
        self.assertNotIn("337 NO", dumped)
        self.assertEqual(result["checkout"], "NOT_MINTED")
        self.assertEqual(result["sends"], 0)

    def test_cli_json(self) -> None:
        if not slot.HARBORLINE.is_file():
            self.skipTest("Harborline waitlist-slot sheet not in this tree")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "pack_harborline_waitlist_slot.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["verdict"], "HARBORLINE_WAITLIST_SLOT_OK")
        self.assertIs(data["gate"], False)
        self.assertEqual(data["receipt_id"], "cursor-pack-harborline-waitlist-slot-20260902-01")


if __name__ == "__main__":
    unittest.main()
