#!/usr/bin/env python3
"""Unique leftover helper for the landed Harborline map-helper pointer. Does not remint."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_harborline_map_helper_pointer as pointer  # noqa: E402


class BusinessPackHarborlineMapHelperPointerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = pointer.load_law()
        self.block = pointer.instances_block(self.law)
        self.waitlist = pointer.waitlist_block(self.law)
        self.row = pointer.harborline_row(self.block)
        self.result = pointer.classify_pointer(self.law)
        self.receipt = (
            ROOT
            / "p"
            / "cursor-business-pack-harborline-map-helper-pointer-helper-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.pointer_receipt = (
            ROOT
            / "p"
            / "cursor-business-pack-harborline-map-helper-pointer-20260902-01.md"
        ).read_text(encoding="utf-8")

    def test_helper_cites_pointer_without_remint(self) -> None:
        self.assertEqual(self.law["id"], "cursor-business-packs-unique-20260902-01")
        self.assertEqual(self.block["id"], "cursor-business-pack-instance-catalog-20260902-01")
        self.assertEqual(
            self.block["harborline_tally_pack_map_pointer"],
            "cursor-business-pack-harborline-tally-map-pointer-20260902-01",
        )
        self.assertEqual(
            self.block["harborline_tally_pack_map_pointer_helper"],
            "host/business_pack_harborline_tally_map_pointer.py",
        )
        self.assertEqual(
            self.waitlist["id"],
            "cursor-business-pack-waitlist-pointer-20260902-01",
        )
        self.assertNotEqual(
            self.result["id"],
            "cursor-business-pack-harborline-map-helper-pointer-20260902-01",
        )
        self.assertNotEqual(self.result["id"], self.block["id"])
        self.assertIs(self.law["gate"], False)
        self.assertIs(self.law["commons_admission"], False)
        self.assertTrue(self.result["pointer_ok"])
        self.assertTrue(self.result["did_not_remint_pointer"])

    def test_keep_main_remint_7754(self) -> None:
        self.assertTrue(self.result["keep_main"])
        self.assertEqual(self.result["keep_main_pr"], 7754)
        self.assertEqual(self.result["original_sidewalk_lotribbon_receipt"], "2c584983")
        self.assertIn("KEEP MAIN", self.pointer_receipt)
        self.assertIn("#7754", self.pointer_receipt)
        self.assertIn("2c584983", self.pointer_receipt)
        self.assertIn("KEEP MAIN", self.receipt)
        self.assertIn("#7754", self.receipt)

    def test_intact_blobs_stay_put(self) -> None:
        self.assertTrue(self.result["blobs_match"])
        self.assertIs(self.result["live_instance_blobs_not_pinned"], True)
        self.assertTrue(
            self.result["blobs"]["host/harborline_tally_pack_map.py"].startswith("a7a49b77")
        )
        self.assertTrue(
            self.result["blobs"]["packs/desk-website-service-20260902-01/door.html"].startswith(
                "d3d6fcc7"
            )
        )
        self.assertTrue(self.result["blobs"]["packs/waitlist.html"].startswith("bdcaa7ea"))
        self.assertTrue(
            self.result["blobs"][
                "p/cursor-business-pack-harborline-map-helper-pointer-20260902-01.md"
            ].startswith("269e874a")
        )
        self.assertEqual(
            self.result["observed_at_land"][
                "host/business_pack_harborline_tally_map_pointer.py"
            ],
            "5f3d59ba",
        )
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
        self.assertTrue(self.result["did_not_overwrite_map_helper"])
        self.assertTrue(self.result["did_not_overwrite_map_pointer_helper"])
        self.assertTrue(self.result["did_not_overwrite_sidecar_leftover"])
        self.assertTrue(self.result["did_not_overwrite_harborline_door"])
        self.assertTrue(self.result["did_not_overwrite_waitlist"])
        self.assertTrue(self.result["did_not_overwrite_tally_helper"])
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertTrue((ROOT / "host" / "business_pack_harborline_tally_map.py").is_file())
        self.assertNotIn("337 NO", json.dumps(self.result))

    def test_receipt_does_not_remint_pointer(self) -> None:
        self.assertIn(
            "cursor-business-pack-harborline-map-helper-pointer-20260902-01",
            self.receipt,
        )
        self.assertIn("did not remint", self.receipt.lower())
        self.assertIn("NOT_MINTED", self.receipt)
        self.assertIn("a889db44", self.receipt)
        self.assertIn("5f3d59ba", self.receipt)
        self.assertIn("cursor-business-pack-instance-catalog-20260902-01", self.receipt)
        self.assertIn("636e2e2fd", self.pointer_receipt)
        self.assertNotEqual(
            self.receipt.split("id:", 1)[1].splitlines()[0].strip(),
            "cursor-business-pack-harborline-map-helper-pointer-20260902-01",
        )

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_harborline_map_helper_pointer.py"),
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
            "cursor-business-pack-harborline-map-helper-pointer-helper-20260902-01",
        )
        self.assertEqual(
            data["pointer_id"],
            "cursor-business-pack-harborline-map-helper-pointer-20260902-01",
        )
        self.assertEqual(data["checkout"], "NOT_MINTED")
        self.assertTrue(data["did_not_remint_pointer"])
        self.assertTrue(data["keep_main"])
        self.assertTrue(data["blobs_match"])
        self.assertIs(data["live_instance_blobs_not_pinned"], True)


if __name__ == "__main__":
    unittest.main()
