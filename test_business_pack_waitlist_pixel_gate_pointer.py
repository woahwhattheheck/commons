#!/usr/bin/env python3
"""Unique business_pack leftover after the landed pack_* pixel-gate pointer."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_waitlist_pixel_gate_pointer as pointer  # noqa: E402


class BusinessPackWaitlistPixelGatePointerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = pointer.load_law()
        self.block = pointer.waitlist_block(self.law)
        self.catalog = pointer.instances_block(self.law)
        self.result = pointer.classify_pointer(self.law)
        self.receipt = (
            ROOT
            / "p"
            / "cursor-business-pack-waitlist-pixel-gate-classifier-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.pointer_receipt = (
            ROOT
            / "p"
            / "cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.peer_helper_receipt = (
            ROOT
            / "p"
            / "cursor-business-pack-waitlist-pixel-gate-pointer-helper-20260902-01.md"
        ).read_text(encoding="utf-8")

    def test_helper_cites_pointer_without_remint(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(
            self.catalog["id"], "cursor-business-pack-instance-catalog-20260902-01"
        )
        self.assertEqual(
            self.block["id"], "cursor-business-pack-waitlist-pointer-20260902-01"
        )
        self.assertEqual(
            self.block["pixel_gate_pointer"],
            "cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01",
        )
        self.assertEqual(
            self.block["pixel_gate_receipt"],
            "cursor-pack-waitlist-pixel-gate-20260902-01",
        )
        self.assertNotEqual(self.result["id"], self.block["pixel_gate_pointer"])
        self.assertNotEqual(self.result["id"], self.result["peer_helper_id"])
        self.assertNotEqual(self.result["id"], self.block["id"])
        self.assertNotEqual(self.result["id"], self.catalog["id"])
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertTrue(self.result["pointer_ok"])
        self.assertTrue(self.result["did_not_remint_pointer"])
        self.assertTrue(self.result["did_not_remint_peer_helper"])
        self.assertTrue(self.result["did_not_remint_catalog"])
        self.assertTrue(self.result["did_not_remint_waitlist"])

    def test_pixel_gate_files_stay_with_bc_31c8ef9a(self) -> None:
        self.assertEqual(self.block["pixel_gate_helper"], "host/pack_waitlist_pixel_gate.py")
        self.assertEqual(self.block["pixel_gate_claimed_by"], "bc-31c8ef9a")
        self.assertEqual(self.block["pixel_gate_sha"], "314cb051e")
        self.assertIs(self.block["did_not_write_pixel_gate_paths"], True)
        self.assertTrue(self.result["files_cleared_to_bc_31c8ef9a"])
        self.assertTrue(self.result["did_not_write_pixel_gate_paths"])
        self.assertTrue(self.result["did_not_overwrite_waitlist_html"])
        self.assertTrue(self.result["did_not_overwrite_thanks_html"])
        self.assertTrue(self.result["did_not_overwrite_peer_pack_helper"])
        self.assertTrue(self.result["ccpa_opt_out_blocks_thanks_pixels"])
        self.assertTrue(self.result["empty_slots_load_nothing"])
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertNotIn("host/pack_waitlist_pixel_gate.py", pointer.THIS_SEAT_PATHS)
        self.assertNotIn("host/pack_waitlist_pixel_gate_pointer.py", pointer.THIS_SEAT_PATHS)
        self.assertIn("host/pack_waitlist_pixel_gate.py", pointer.DO_NOT_WRITE)
        self.assertIn("packs/waitlist.html", pointer.DO_NOT_WRITE)
        self.assertIn("packs/thanks.html", pointer.DO_NOT_WRITE)
        self.assertNotIn("337 NO", json.dumps(self.result))

    def test_intact_blobs_stay_put(self) -> None:
        self.assertTrue(self.result["blobs_match"])
        self.assertTrue(
            self.result["blobs"]["host/pack_waitlist_pixel_gate.py"].startswith("4df0f64e")
        )
        self.assertTrue(
            self.result["blobs"]["host/pack_waitlist_pixel_gate_pointer.py"].startswith(
                "b3f26525"
            )
        )
        self.assertTrue(self.result["blobs"]["packs/waitlist.html"].startswith("bdcaa7ea"))
        self.assertTrue(self.result["blobs"]["packs/thanks.html"].startswith("7ec0bf86"))
        self.assertTrue(
            self.result["blobs"][
                "p/cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01.md"
            ].startswith("6f981cf8")
        )
        self.assertTrue(
            self.result["blobs"][
                "p/cursor-business-pack-waitlist-pixel-gate-pointer-helper-20260902-01.md"
            ].startswith("af68f245")
        )

    def test_receipt_does_not_remint_pointer_or_peer_helper(self) -> None:
        self.assertIn(
            "cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01", self.receipt
        )
        self.assertIn(
            "cursor-business-pack-waitlist-pixel-gate-pointer-helper-20260902-01",
            self.receipt,
        )
        self.assertIn("did not remint", self.receipt.lower())
        self.assertIn("NOT_MINTED", self.receipt)
        self.assertIn("4df0f64e", self.receipt)
        self.assertIn("b3f26525", self.receipt)
        self.assertIn("cursor-business-pack-instance-catalog-20260902-01", self.receipt)
        self.assertIn("314cb051e", self.pointer_receipt)
        self.assertIn("pack_*", self.peer_helper_receipt)
        self.assertNotEqual(
            self.receipt.split("id:", 1)[1].splitlines()[0].strip(),
            "cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01",
        )
        self.assertNotEqual(
            self.receipt.split("id:", 1)[1].splitlines()[0].strip(),
            "cursor-business-pack-waitlist-pixel-gate-pointer-helper-20260902-01",
        )

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_waitlist_pixel_gate_pointer.py"),
            ],
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
            "cursor-business-pack-waitlist-pixel-gate-classifier-20260902-01",
        )
        self.assertEqual(
            data["pointer_id"],
            "cursor-business-pack-waitlist-pixel-gate-pointer-20260902-01",
        )
        self.assertEqual(data["checkout"], "NOT_MINTED")
        self.assertTrue(data["did_not_remint_pointer"])
        self.assertTrue(data["did_not_remint_peer_helper"])
        self.assertTrue(data["did_not_remint_catalog"])
        self.assertTrue(data["did_not_remint_waitlist"])
        self.assertTrue(data["blobs_match"])
        self.assertTrue(data["files_cleared_to_bc_31c8ef9a"])


if __name__ == "__main__":
    unittest.main()
