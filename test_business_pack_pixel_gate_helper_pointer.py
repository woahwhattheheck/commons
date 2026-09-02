#!/usr/bin/env python3
"""Leftover helper: landed pixel-gate helper catalog pointer stays that peer."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_pixel_gate_helper_pointer as pointer  # noqa: E402


class BusinessPackPixelGateHelperPointerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = pointer.load_law()
        self.waitlist = pointer.waitlist_block(self.law)
        self.result = pointer.classify_pointer(self.law)
        self.helper_receipt = (
            ROOT
            / "p"
            / "cursor-business-pack-pixel-gate-helper-pointer-helper-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.pointer_receipt = (
            ROOT / "p" / "cursor-business-pack-pixel-gate-helper-pointer-20260902-01.md"
        ).read_text(encoding="utf-8")

    def test_cites_landed_pointer_without_overwrite(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(
            self.waitlist["pixel_gate_helper_pointer"],
            "cursor-business-pack-pixel-gate-helper-pointer-20260902-01",
        )
        self.assertEqual(
            self.waitlist["pixel_gate_pointer_helper"],
            "host/pack_waitlist_pixel_gate_pointer.py",
        )
        self.assertEqual(self.result["id"], pointer.HELPER_ID)
        self.assertEqual(self.result["pointer_id"], pointer.POINTER_ID)
        self.assertTrue(self.result["pointer_ok"])
        self.assertTrue(self.result["did_not_overwrite_leftover_helper"])
        self.assertTrue(self.result["did_not_overwrite_complementary_helper"])
        self.assertTrue(self.result["did_not_remint_pixel_gate_helper_pointer"])
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertNotEqual(self.result["id"], self.waitlist["pixel_gate_helper_pointer"])

    def test_does_not_steal_or_remint(self) -> None:
        self.assertNotIn(
            "host/pack_waitlist_pixel_gate_pointer.py", pointer.THIS_SEAT_PATHS
        )
        self.assertNotIn(
            "p/cursor-business-pack-pixel-gate-helper-pointer-20260902-01.md",
            pointer.THIS_SEAT_PATHS,
        )
        self.assertTrue((ROOT / "host" / "pack_waitlist_pixel_gate_pointer.py").is_file())
        self.assertIn("a866c00e", self.helper_receipt)
        self.assertIn("b3f26525", self.pointer_receipt)
        self.assertIn("NOT_MINTED", self.helper_receipt)
        self.assertNotIn("337 NO", self.helper_receipt)

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "business_pack_pixel_gate_helper_pointer.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertTrue(data["pointer_ok"])
        self.assertEqual(data["id"], pointer.HELPER_ID)
        self.assertEqual(data["leftover_helper"], "host/pack_waitlist_pixel_gate_pointer.py")
        self.assertEqual(data["checkout"], "NOT_MINTED")


if __name__ == "__main__":
    unittest.main()
