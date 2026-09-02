#!/usr/bin/env python3
"""Waitlist pointer cites bc-31c8ef9a files and does not write them."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_waitlist_pointer as pointer  # noqa: E402

OWNER_PATHS = (
    "packs/waitlist.html",
    "packs/_template/waitlist-slot.md",
    "ground/BUSINESS_PACK_WAITLIST.json",
    "host/pack_waitlist.py",
    "test_pack_waitlist.py",
    "p/scout-demand-pack-door-waitlist-20260902-01.md",
    "land/pack-waitlist-20260902.md",
)
THIS_SEAT = (
    "ground/BUSINESS_PACK_WAITLIST_POINTER.json",
    "host/pack_waitlist_pointer.py",
    "test_pack_waitlist_pointer.py",
    "land/pack-waitlist-pointer-20260902.md",
    "p/cursor-pack-waitlist-pointer-helper-20260902-01.md",
)
PEER_POINTER = "p/cursor-business-pack-waitlist-pointer-20260902-01.md"
PEER_POINTER_BLOB = "0af23b1989ce004935fabb75e865df339b6e08b6"


class PackWaitlistPointerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = pointer.load_pointer()
        self.result = pointer.classify()
        self.unique = json.loads((ROOT / "ground" / "BUSINESS_PACKS.json").read_text(encoding="utf-8"))
        self.card = (ROOT / "ground" / "BUSINESS_PACKS.md").read_text(encoding="utf-8")

    def test_pointer_cites_owner_and_does_not_write_waitlist_files(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-pack-waitlist-pointer-20260902-01")
        self.assertEqual(self.law["scout_demand_id"], "scout-demand-pack-door-waitlist-20260902-01")
        self.assertEqual(self.law["owner_seat"], "bc-31c8ef9a")
        self.assertIs(self.law["pointer_only"], True)
        self.assertIs(self.law["did_not_remint_scout_demand"], True)
        self.assertIs(self.law["did_not_write_owner_paths"], True)
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        self.assertEqual(list(self.law["owner_paths"]), list(OWNER_PATHS))
        self.assertIs(self.result["gate"], False)
        self.assertIs(self.result["commons_admission"], False)
        self.assertTrue(self.result["did_not_write_owner_paths"])
        self.assertTrue(self.result["did_not_remint_scout_demand"])
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        for rel in OWNER_PATHS:
            self.assertFalse(
                any(rel == mine for mine in THIS_SEAT),
                f"owner path {rel} collided with this seat",
            )
        helper_text = (ROOT / "host" / "pack_waitlist_pointer.py").read_text(encoding="utf-8")
        self.assertNotIn('open("packs/waitlist.html"', helper_text)
        self.assertNotIn("write_text", helper_text)
        self.assertNotIn("Path.write_text", helper_text)

    def test_this_seat_files_exist_and_peer_pointer_is_not_reminted(self) -> None:
        for rel in THIS_SEAT:
            self.assertTrue((ROOT / rel).is_file(), rel)
        peer = ROOT / PEER_POINTER
        self.assertTrue(peer.is_file())
        self.assertEqual(pointer.git_blob_sha(peer), PEER_POINTER_BLOB)
        receipt = peer.read_text(encoding="utf-8")
        self.assertIn("id: cursor-business-pack-waitlist-pointer-20260902-01", receipt)
        self.assertNotIn("id: scout-demand-pack-door-waitlist-20260902-01", receipt)
        helper_receipt = (ROOT / "p" / "cursor-pack-waitlist-pointer-helper-20260902-01.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("id: cursor-pack-waitlist-pointer-helper-20260902-01", helper_receipt)
        self.assertNotIn("id: cursor-business-pack-waitlist-pointer-20260902-01", helper_receipt.split("---", 2)[1])

    def test_thanks_door_not_overwritten(self) -> None:
        thanks = self.result["thanks_door"]
        self.assertTrue(thanks["present"])
        self.assertTrue(thanks["blob_prefix_ok"])
        self.assertTrue(thanks["blob"].startswith("7ec0bf86"))
        self.assertTrue(thanks["did_not_overwrite"])
        self.assertIn("packs/thanks.html", pointer.DO_NOT_OVERWRITE)
        self.assertEqual(self.law["thanks_door"], "packs/thanks.html")
        self.assertIs(self.law["did_not_overwrite_thanks_door"], True)

    def test_tally_helper_stays_single_owner_harborline_similar_not_clone(self) -> None:
        self.assertTrue(self.result["tally_helper_present"])
        self.assertTrue(self.result["tally_helper_single_owner"])
        self.assertTrue(self.result["did_not_overwrite_tally_helper"])
        self.assertIn("host/business_pack_desk_instance.py", pointer.DO_NOT_OVERWRITE)
        self.assertIn("host/business_pack_waitlist_pointer.py", pointer.DO_NOT_OVERWRITE)
        self.assertNotEqual(Path(pointer.__file__).name, "business_pack_waitlist_pointer.py")
        self.assertTrue(self.result["peer_helper_present"])
        self.assertTrue(self.result["did_not_overwrite_peer_helper"])
        harbor = self.result["harborline"]
        self.assertEqual(harbor["harborline_brand"], "Harborline Local Sites")
        self.assertEqual(harbor["tally_brand"], "Sidewalk Signal")
        self.assertTrue(harbor["similar_is_not_clone"])
        self.assertFalse(harbor["clone_stamp"])
        self.assertNotEqual(harbor["harborline_brand"], harbor["tally_brand"])

    def test_unique_pack_law_already_cites_the_landed_pointer(self) -> None:
        block = self.unique["waitlist"]
        self.assertEqual(block["id"], "cursor-business-pack-waitlist-pointer-20260902-01")
        self.assertEqual(block["claimed_by"], "bc-31c8ef9a")
        self.assertEqual(block["checkout"], "NOT_MINTED")
        self.assertIs(block["did_not_remint_scout_demand"], True)
        self.assertIs(block["did_not_write_waitlist_paths"], True)
        self.assertIs(block["did_not_overwrite_thanks_html"], True)
        self.assertIs(block["did_not_steal_desk_helper"], True)
        self.assertIs(block["did_not_wrap_harborline"], True)
        self.assertEqual(self.result["unique_pack_waitlist_pointer_id"], block["id"])
        self.assertEqual(self.result["owner_seat"], "bc-31c8ef9a")
        self.assertIn("packs/waitlist.html", self.card)
        self.assertIn("bc-31c8ef9a", self.card)
        self.assertIn("scout-demand-pack-door-waitlist-20260902-01", self.card)
        self.assertNotIn("waitlist_pointer", self.unique)


if __name__ == "__main__":
    unittest.main()
