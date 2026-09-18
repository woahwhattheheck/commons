#!/usr/bin/env python3
"""CLEAR Harborline + thanks-channels: TALLY helper stays single-owner."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import desk_website_service_pack as desk  # noqa: E402
import pack_thanks_pixel as thanks  # noqa: E402

TALLY_HELPER = "host/business_pack_desk_instance.py"
TALLY_TEST = "test_business_pack_desk_instance.py"
TALLY_PACK = "packs/sidewalk-signal-web-desk-20260902-01"
HARBORLINE_HELPER = "host/desk_website_service_pack.py"
PEER_DOOR = "packs/thanks.html"
RESERVED = (TALLY_HELPER, TALLY_TEST, TALLY_PACK)


class HarborlineThanksClearTest(unittest.TestCase):
    def setUp(self) -> None:
        self.desk_law = desk.load_law()
        self.instance = desk.load_instance()
        self.channels = thanks.load_channels()

    def test_tally_desk_helper_paths_are_not_harborline_writes(self) -> None:
        self.assertEqual(self.desk_law["helper"], HARBORLINE_HELPER)
        self.assertEqual(self.desk_law["peer_tally_instance"], TALLY_PACK)
        self.assertIs(self.desk_law["similar_is_not_clone"], True)
        self.assertNotEqual(HARBORLINE_HELPER, TALLY_HELPER)
        self.assertNotEqual(Path(HARBORLINE_HELPER).name, Path(TALLY_HELPER).name)
        harborline_text = "\n".join(
            [
                (ROOT / "host" / "desk_website_service_pack.py").read_text(encoding="utf-8"),
                json.dumps(self.desk_law),
                json.dumps(self.instance),
            ]
        )
        self.assertNotIn(f'open("{TALLY_HELPER}"', harborline_text)
        self.assertNotIn(f"Path({TALLY_HELPER!r})", harborline_text)
        self.assertNotIn("business_pack_desk_instance.py", harborline_text)
        self.assertFalse((ROOT / TALLY_HELPER).is_file() and Path(HARBORLINE_HELPER).resolve() == (ROOT / TALLY_HELPER).resolve())

    def test_harborline_is_similar_not_clone(self) -> None:
        self.assertEqual(self.instance["brand"], "Harborline Local Sites")
        self.assertNotEqual(self.instance["brand"], "Sidewalk Signal")
        self.assertNotIn("Sidewalk Signal", self.instance["brand"])
        self.assertEqual(
            self.instance["sale_id"],
            "desk-website-service-20260902-01-harborline",
        )
        self.assertTrue(str(self.instance["door"]).startswith("packs/desk-website-service-20260902-01/"))
        self.assertFalse(str(self.instance["door"]).startswith(TALLY_PACK))
        result = desk.classify()
        self.assertFalse(result["clone_stamp"])
        self.assertTrue(result["marketing_uniqueness_ok"])

    def test_thanks_channels_did_not_overwrite_peer_door(self) -> None:
        self.assertEqual(
            list(thanks.DO_NOT_OVERWRITE),
            [
                PEER_DOOR,
                "ground/BUSINESS_PACK_THANKS.json",
                "host/business_pack_thanks.py",
            ],
        )
        self.assertEqual(self.channels["peer_door"], PEER_DOOR)
        self.assertIs(self.channels["did_not_overwrite_peer_door"], True)
        peer = thanks.classify_peer_door()
        self.assertTrue(peer["present"])
        self.assertTrue(peer["pixel_id_empty"])
        self.assertEqual(peer["static_third_party_scripts"], [])
        self.assertTrue(peer["empty_loads_zero_third_party_scripts"])
        self.assertTrue(peer["did_not_overwrite"])
        door = (ROOT / PEER_DOOR).read_text(encoding="utf-8")
        self.assertNotIn("ads-twitter.com", door)
        self.assertNotIn("analytics.tiktok.com", door)
        self.assertNotIn("connect.facebook.net", door)

    def test_reserved_tally_names_stay_outside_harborline_instance_dir(self) -> None:
        pack_dir = ROOT / "packs" / "desk-website-service-20260902-01"
        names = {path.name for path in pack_dir.rglob("*") if path.is_file()}
        self.assertNotIn("business_pack_desk_instance.py", names)
        self.assertNotIn("index.html", names)  # TALLY claimed door index.html; Harborline uses door.html
        self.assertTrue((pack_dir / "door.html").is_file())


if __name__ == "__main__":
    unittest.main()
