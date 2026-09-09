#!/usr/bin/env python3
"""Unique helper for the landed waitlist pointer. Does not remint the CLAIM id."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_waitlist_pointer as pointer  # noqa: E402


class BusinessPackWaitlistPointerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = pointer.load_law()
        self.block = pointer.waitlist_block(self.law)
        self.card = (ROOT / "ground" / "BUSINESS_PACKS.md").read_text(encoding="utf-8")
        self.door = (ROOT / "business-packs.html").read_text(encoding="utf-8")
        self.receipt = (
            ROOT / "p" / "cursor-business-pack-waitlist-pointer-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.result = pointer.classify_pointer(self.law)

    def test_pointer_cites_unique_pack_without_remint(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(self.block["id"], "cursor-business-pack-waitlist-pointer-20260902-01")
        self.assertEqual(
            self.block["scout_demand_id"],
            "scout-demand-pack-door-waitlist-20260902-01",
        )
        self.assertIs(self.block["did_not_remint_scout_demand"], True)
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertTrue(self.result["pointer_ok"])
        self.assertEqual(self.result["unique_pack_id"], "cursor-business-packs-unique-20260902-01")
        self.assertNotEqual(self.block["id"], self.block["scout_demand_id"])

    def test_waitlist_files_are_cleared_to_bc_31c8ef9a(self) -> None:
        self.assertEqual(self.result["files_owner"], "bc-31c8ef9a")
        self.assertIn(self.block.get("claimed_by") or self.block.get("files_owner"), ("bc-31c8ef9a",))
        self.assertTrue(
            self.block.get("did_not_write_waitlist_paths") is True
            or self.block.get("did_not_write_waitlist_html") is True
        )
        self.assertEqual(
            self.block.get("door") or self.block.get("waitlist_door"),
            "packs/waitlist.html",
        )
        self.assertTrue(self.result["files_cleared_to_bc_31c8ef9a"])
        self.assertTrue(self.result["did_not_write_waitlist_html"])
        self.assertNotIn("host/pack_waitlist.py", pointer.__file__.replace("\\", "/"))
        self.assertTrue(
            (ROOT / "p" / "cursor-business-pack-waitlist-pointer-20260902-01.md").is_file()
        )
        self.assertFalse(
            (ROOT / "p" / "scout-demand-pack-door-waitlist-20260902-01.md").is_file()
            and self.receipt.startswith("---\nid: scout-demand-pack-door-waitlist-20260902-01")
        )

    def test_excluded_state_waitlist_is_not_checkout_or_auth(self) -> None:
        self.assertEqual(self.result["excluded_state_shows"], "waitlist_not_checkout")
        self.assertIs(self.result["zero_sends"], True)
        self.assertIs(self.result["no_auth"], True)
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertIs(self.result["agents_spend_ads"], False)
        self.assertIs(self.result["commons_admission"], False)
        self.assertNotIn("337 NO", json.dumps(self.block))
        self.assertNotIn("337 NO", self.card)
        self.assertNotIn("337 NO", self.door)
        self.assertNotIn("<form", self.door)

    def test_card_and_door_point_without_writing_the_waitlist(self) -> None:
        self.assertIn("scout-demand-pack-door-waitlist-20260902-01", self.card)
        self.assertIn("bc-31c8ef9a", self.card)
        self.assertIn("packs/waitlist.html", self.card)
        self.assertIn("NOT_MINTED", self.card)
        self.assertIn("scout-demand-pack-door-waitlist-20260902-01", self.door)
        self.assertIn("bc-31c8ef9a", self.door)
        self.assertIn("waitlist", self.door.lower())
        if (ROOT / "packs" / "waitlist.html").is_file():
            self.assertIn('href="./packs/waitlist.html"', self.door)
        else:
            self.assertNotIn('href="./packs/waitlist.html"', self.door)
            self.assertNotIn('href="packs/waitlist.html"', self.door)
        self.assertIn("NOT_MINTED", self.door)
        self.assertIn("bc-31c8ef9a", self.receipt)
        self.assertIn("packs/waitlist.html", self.receipt)
        self.assertIn("cursor-business-packs-unique-20260902-01", self.receipt)

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "business_pack_waitlist_pointer.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertIs(data["gate"], False)
        self.assertIs(data["commons_admission"], False)
        self.assertTrue(data["pointer_ok"])
        self.assertEqual(data["files_owner"], "bc-31c8ef9a")
        self.assertEqual(data["checkout"], "NOT_MINTED")
        self.assertTrue(data["did_not_write_waitlist_html"])
        self.assertTrue(data["did_not_remint_scout_demand"])


if __name__ == "__main__":
    unittest.main()
