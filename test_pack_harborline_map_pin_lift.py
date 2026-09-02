#!/usr/bin/env python3
"""Unique leftover: Harborline map helpers observe TALLY/LEAD blobs at land time."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_harborline_map_helper_pointer as map_helper_pointer  # noqa: E402
import business_pack_harborline_tally_map as sidecar  # noqa: E402
import business_pack_harborline_tally_map_pointer as map_pointer  # noqa: E402


class PackHarborlineMapPinLiftTest(unittest.TestCase):
    def test_three_leftovers_do_not_live_pin_tally_or_lotribbon(self) -> None:
        sidecar_out = sidecar.classify_pointer()
        pointer_out = map_pointer.classify_pointer()
        helper_out = map_helper_pointer.classify_pointer()
        for result in (sidecar_out, pointer_out, helper_out):
            self.assertIs(result["live_instance_blobs_not_pinned"], True)
            self.assertTrue(result["pointer_ok"])
            self.assertEqual(
                result["observed_at_land"][
                    "packs/sidewalk-signal-web-desk-20260902-01/index.html"
                ],
                "638e60b4",
            )
            self.assertEqual(
                result["observed_at_land"]["host/business_pack_desk_instance.py"],
                "a550ae1b",
            )
            self.assertEqual(
                result["observed_at_land"][
                    "packs/lotribbon-greetings-20260902-01/index.html"
                ],
                "ac60db02",
            )
            self.assertTrue(
                result["blobs"]["host/harborline_tally_pack_map.py"].startswith("a889db44")
            )
            self.assertTrue(
                result["blobs"]["packs/desk-website-service-20260902-01/door.html"].startswith(
                    "d3d6fcc7"
                )
            )
        sidecar_text = (ROOT / "host" / "business_pack_harborline_tally_map.py").read_text(
            encoding="utf-8"
        )
        pointer_text = (
            ROOT / "host" / "business_pack_harborline_tally_map_pointer.py"
        ).read_text(encoding="utf-8")
        helper_text = (
            ROOT / "host" / "business_pack_harborline_map_helper_pointer.py"
        ).read_text(encoding="utf-8")
        for text in (sidecar_text, pointer_text, helper_text):
            self.assertIn("OBSERVED_AT_LAND", text)
            self.assertIn("live_instance_blobs_not_pinned", text)
            self.assertNotIn("write_text", text)
        receipt = (
            ROOT / "p" / "cursor-pack-harborline-map-pin-lift-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.assertIn("cursor-pack-harborline-map-pin-lift-20260902-01", receipt)
        self.assertIn("NOT_MINTED", receipt)
        self.assertIn("638e60b4", receipt)
        self.assertIn("a550ae1b", receipt)
        self.assertIn("1788331796.003639", receipt)

    def test_cli_json_sidecar(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "business_pack_harborline_tally_map.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertIs(data["live_instance_blobs_not_pinned"], True)
        self.assertTrue(data["pointer_ok"])
        self.assertEqual(data["checkout"], "NOT_MINTED")
        self.assertNotIn("337 NO", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
