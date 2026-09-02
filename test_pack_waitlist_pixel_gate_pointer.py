#!/usr/bin/env python3
"""Pointer leftover cites bc-31c8ef9a pixel-gate and does not remint it."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_waitlist_pixel_gate_pointer as pointer  # noqa: E402


OWNER_PATHS = (
    "packs/waitlist.html",
    "host/pack_waitlist_pixel_gate.py",
    "test_pack_waitlist_pixel_gate.py",
    "p/cursor-pack-waitlist-pixel-gate-20260902-01.md",
)
THIS_SEAT = (
    "ground/BUSINESS_PACK_WAITLIST_PIXEL_GATE_POINTER.json",
    "host/pack_waitlist_pixel_gate_pointer.py",
    "test_pack_waitlist_pixel_gate_pointer.py",
    "land/pack-waitlist-pixel-gate-pointer-20260902.md",
    "p/cursor-business-pack-waitlist-pixel-gate-pointer-helper-20260902-01.md",
)
POINTER_RECEIPT = "p/cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01.md"


class PackWaitlistPixelGatePointerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = pointer.load_pointer()
        self.result = pointer.classify()
        self.unique = json.loads((ROOT / "ground" / "BUSINESS_PACKS.json").read_text(encoding="utf-8"))

    def test_pointer_cites_clear_and_does_not_write_peer_files(self) -> None:
        self.assertEqual(self.law["id"], pointer.POINTER_ID)
        self.assertEqual(self.law["owner_seat"], "bc-31c8ef9a")
        self.assertEqual(self.law["pixel_gate_claimed_by"], "bc-31c8ef9a")
        self.assertEqual(self.law["pixel_gate_sha"], "314cb051e")
        self.assertEqual(self.law["pixel_gate_helper"], "host/pack_waitlist_pixel_gate.py")
        self.assertEqual(self.law["pixel_gate_receipt"], "cursor-pack-waitlist-pixel-gate-20260902-01")
        self.assertEqual(self.law["waitlist_pointer_id"], "cursor-business-pack-waitlist-pointer-20260902-01")
        self.assertEqual(self.law["scout_demand_id"], "scout-demand-pack-door-waitlist-20260902-01")
        self.assertIs(self.law["pointer_only"], True)
        self.assertIs(self.law["did_not_remint_pointer"], True)
        self.assertIs(self.law["did_not_write_pixel_gate_paths"], True)
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        self.assertIs(self.law["agents_mint_pixel_id"], False)
        self.assertIs(self.law["agents_spend_ads"], False)
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.result["gate"], False)
        self.assertIs(self.result["commons_admission"], False)
        self.assertTrue(self.result["files_cleared_to_bc_31c8ef9a"])
        self.assertTrue(self.result["did_not_remint_pointer"])
        self.assertTrue(self.result["did_not_remint_waitlist_pointer"])
        self.assertTrue(self.result["did_not_write_pixel_gate_paths"])
        self.assertTrue(self.result["ccpa_opt_out_blocks_thanks_pixels"])
        self.assertTrue(self.result["empty_slots_load_nothing"])
        self.assertEqual(self.result["sends"], 0)
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertTrue(self.result["pointer_ok"])
        for rel in OWNER_PATHS:
            self.assertFalse(
                any(rel == mine for mine in THIS_SEAT),
                f"owner path {rel} collided with this seat",
            )
        helper_text = (ROOT / "host" / "pack_waitlist_pixel_gate_pointer.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("write_text", helper_text)
        self.assertNotIn("Path.write_text", helper_text)

    def test_landed_pointer_and_peer_helper_are_not_reminted(self) -> None:
        for rel in THIS_SEAT:
            self.assertTrue((ROOT / rel).is_file(), rel)
        peer = ROOT / POINTER_RECEIPT
        self.assertTrue(peer.is_file())
        self.assertEqual(pointer.git_blob_sha(peer), pointer.POINTER_RECEIPT_BLOB)
        receipt = peer.read_text(encoding="utf-8")
        self.assertIn("id: cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01", receipt)
        self.assertNotIn("id: scout-demand-pack-door-waitlist-20260902-01", receipt)
        helper = ROOT / "host" / "pack_waitlist_pixel_gate.py"
        self.assertTrue(helper.is_file())
        self.assertTrue(pointer.git_blob_sha(helper).startswith("4df0f64e"))
        helper_receipt = (
            ROOT / "p" / "cursor-business-pack-waitlist-pixel-gate-pointer-helper-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "id: cursor-business-pack-waitlist-pixel-gate-pointer-helper-20260902-01",
            helper_receipt,
        )
        self.assertNotIn(
            "id: cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01",
            helper_receipt.split("---", 2)[1],
        )

    def test_waitlist_and_thanks_doors_stay_peer_bytes(self) -> None:
        self.assertTrue(self.result["did_not_overwrite_waitlist_html"])
        self.assertTrue(self.result["did_not_overwrite_thanks_html"])
        self.assertTrue(self.result["waitlist_door"]["blob"].startswith("bdcaa7ea"))
        self.assertTrue(self.result["thanks_door"]["blob"].startswith("7ec0bf86"))
        waitlist = self.unique["waitlist"]
        self.assertEqual(waitlist["pixel_gate_claimed_by"], "bc-31c8ef9a")
        self.assertEqual(
            waitlist["pixel_gate_pointer"],
            "cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01",
        )
        self.assertEqual(waitlist["checkout"], "NOT_MINTED")
        self.assertNotEqual(Path(pointer.__file__).name, "pack_waitlist_pixel_gate.py")

    def test_cli_classifies_cleared_pointer(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "pack_waitlist_pixel_gate_pointer.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["pointer_ok"])
        self.assertEqual(payload["owner_seat"], "bc-31c8ef9a")
        self.assertEqual(payload["checkout"], "NOT_MINTED")
        self.assertNotIn("@", proc.stdout)


if __name__ == "__main__":
    unittest.main()
