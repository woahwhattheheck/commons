#!/usr/bin/env python3
"""Sidecar leftover for the landed Harborline tally-pack map pointer."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_harborline_tally_map as pointer  # noqa: E402


class BusinessPackHarborlineTallyMapHelperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = pointer.load_law()
        self.block = pointer.instance_block(self.law)
        self.result = pointer.classify_pointer(self.law)
        self.door = (ROOT / "business-packs.html").read_text(encoding="utf-8")
        self.card = (ROOT / "ground" / "BUSINESS_PACKS.md").read_text(encoding="utf-8")
        self.claim = (
            ROOT
            / "p"
            / "cursor-business-pack-harborline-tally-map-pointer-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.peer = (
            ROOT
            / "p"
            / "cursor-business-pack-harborline-tally-map-pointer-helper-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.receipt = (
            ROOT
            / "p"
            / "cursor-business-pack-harborline-tally-map-helper-20260902-01.md"
        ).read_text(encoding="utf-8")

    def test_does_not_remint_landed_claim_or_peer_helper(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(self.block["id"], "cursor-business-pack-instance-catalog-20260902-01")
        self.assertEqual(
            self.block["harborline_tally_pack_map_pointer"],
            "cursor-business-pack-harborline-tally-map-pointer-20260902-01",
        )
        self.assertEqual(
            self.block["catalog_waitlist_rows_pointer"],
            "cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01",
        )
        self.assertEqual(
            self.law["waitlist"]["id"],
            "cursor-business-pack-waitlist-pointer-20260902-01",
        )
        self.assertEqual(
            self.block["harborline_tally_map_leftover_helper"],
            "host/business_pack_harborline_tally_map.py",
        )
        self.assertEqual(
            self.block["harborline_tally_pack_map_pointer_helper"],
            "host/business_pack_harborline_tally_map_pointer.py",
        )
        self.assertTrue((ROOT / "host" / "business_pack_harborline_tally_map_pointer.py").is_file())
        self.assertNotEqual(
            self.block["harborline_tally_map_leftover_helper"],
            self.block["harborline_tally_pack_map_pointer_helper"],
        )
        self.assertTrue(self.result["ids_not_reminted"])
        self.assertTrue(self.result["pointer_ok"])
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)

    def test_map_stays_with_bc_31c8ef9a_and_blobs_stay_put(self) -> None:
        row = pointer.landed_row(self.block, "Harborline Local Sites")
        self.assertEqual(self.result["map_owner"], "bc-31c8ef9a")
        self.assertTrue(self.result["files_cleared_to_bc_31c8ef9a"])
        self.assertEqual(self.result["map_helper"], "host/harborline_tally_pack_map.py")
        self.assertEqual(self.result["map_sha"], "35ed9d78f")
        self.assertEqual(row["owned_by"], "bc-31c8ef9a")
        self.assertEqual(row["tally_pack_map"], "host/harborline_tally_pack_map.py")
        self.assertEqual(row["tally_pack_map_receipt"], "cursor-harborline-tally-pack-map-20260902-01")
        self.assertEqual(row["helper"], "host/business_pack_desk_instance.py")
        self.assertIs(self.block["did_not_overwrite_harborline_tally_pack_map"], True)
        self.assertTrue(self.result["blobs_match"])
        self.assertIs(self.result["live_instance_blobs_not_pinned"], True)
        self.assertEqual(self.result["blobs"]["host/harborline_tally_pack_map.py"], "a889db44")
        self.assertEqual(
            self.result["blobs"]["p/cursor-business-pack-harborline-tally-map-pointer-20260902-01.md"],
            "e38f1251",
        )
        self.assertEqual(
            self.result["blobs"][
                "p/cursor-business-pack-harborline-tally-map-pointer-helper-20260902-01.md"
            ],
            "6ec23344",
        )
        self.assertEqual(
            self.result["blobs"]["packs/desk-website-service-20260902-01/door.html"],
            "d3d6fcc7",
        )
        self.assertEqual(self.result["blobs"]["packs/waitlist.html"], "bdcaa7ea")
        self.assertEqual(
            self.result["observed_at_land"]["host/business_pack_desk_instance.py"],
            "a550ae1b",
        )
        self.assertEqual(
            self.result["observed_at_land"][
                "packs/sidewalk-signal-web-desk-20260902-01/index.html"
            ],
            "638e60b4",
        )
        self.assertEqual(
            self.result["observed_at_land"][
                "packs/lotribbon-greetings-20260902-01/index.html"
            ],
            "ac60db02",
        )
        self.assertIn(
            "host/business_pack_desk_instance.py",
            self.result["this_seat_does_not_write"],
        )
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertIs(self.result["agents_spend_ads"], False)
        self.assertIs(self.result["no_auth"], True)
        self.assertNotIn("337 NO", json.dumps(self.block))
        self.assertNotIn("<form", self.door)
        self.assertIn("password", self.door)

    def test_card_door_receipt_point_without_stealing_files(self) -> None:
        self.assertIn("bc-31c8ef9a", self.door)
        self.assertIn("harborline_tally_pack_map.py", self.door)
        self.assertIn("NOT_MINTED", self.door)
        self.assertIn("bc-31c8ef9a", self.card)
        self.assertIn("harborline_tally_pack_map.py", self.card)
        self.assertIn("35ed9d78f", self.card)
        self.assertIn("business_pack_harborline_tally_map.py", self.card)
        self.assertIn("e38f1251", self.receipt)
        self.assertIn("6ec23344", self.receipt)
        self.assertIn("bc-31c8ef9a", self.receipt)
        self.assertIn("cursor-business-pack-harborline-tally-map-pointer-20260902-01", self.receipt)
        self.assertIn("not reminted", self.receipt)
        self.assertIn("NOT_MINTED", self.receipt)
        self.assertIn("id: cursor-business-pack-harborline-tally-map-pointer-20260902-01", self.claim)
        self.assertIn("id: cursor-business-pack-harborline-tally-map-pointer-helper-20260902-01", self.peer)

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "business_pack_harborline_tally_map.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertIs(data["gate"], False)
        self.assertIs(data["commons_admission"], False)
        self.assertTrue(data["pointer_ok"])
        self.assertTrue(data["catalog_only"])
        self.assertEqual(data["id"], "cursor-business-pack-harborline-tally-map-helper-20260902-01")
        self.assertEqual(
            data["pointer_id"],
            "cursor-business-pack-harborline-tally-map-pointer-20260902-01",
        )
        self.assertEqual(data["map_owner"], "bc-31c8ef9a")
        self.assertEqual(data["checkout"], "NOT_MINTED")
        self.assertIs(data["live_instance_blobs_not_pinned"], True)


if __name__ == "__main__":
    unittest.main()
