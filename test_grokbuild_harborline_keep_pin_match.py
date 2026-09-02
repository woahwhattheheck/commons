#!/usr/bin/env python3
"""Unique leftover: MATCH Harborline KEEP-pins to live pack-map a7a49b77."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import grokbuild_harborline_keep_pin_match as match  # noqa: E402


class GrokbuildHarborlineKeepPinMatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.result = match.classify_match()
        self.receipt = (
            ROOT / "p" / "grokbuild-harborline-keep-pin-match-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.helper = (
            ROOT / "host" / "grokbuild_harborline_keep_pin_match.py"
        ).read_text(encoding="utf-8")

    def test_match_ok_live_pins(self) -> None:
        self.assertTrue(self.result["match_ok"], msg=self.result)
        self.assertIs(self.result["gate"], False)
        self.assertIs(self.result["commons_admission"], False)
        self.assertIs(self.result["no_auth"], True)
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertEqual(self.result["sends"], 0)
        self.assertEqual(self.result["pack_map_blob"], "a7a49b77")
        self.assertEqual(self.result["pack_map_test_blob"], "68b4fce1")
        self.assertTrue(self.result["did_not_remint_pack_map"])
        self.assertTrue(self.result["did_not_remint_peer_receipts"])
        self.assertTrue(self.result["did_not_overwrite_harborline_door"])
        self.assertTrue(self.result["did_not_overwrite_waitlist"])
        self.assertTrue(self.result["keep_main"])
        self.assertEqual(self.result["keep_main_pr"], 7754)
        self.assertTrue(self.result["pointer_ok"])
        self.assertEqual(self.result["rating_verdict"], "HARBORLINE_RATING_OK")
        self.assertEqual(self.result["waitlist_verdict"], "HARBORLINE_WAITLIST_SLOT_OK")
        self.assertEqual(self.result["lotribbon_verdict"], "LOTRIBBON_RATING_OK")
        self.assertTrue(self.result["never_say_leftover_present"])
        self.assertEqual(
            self.result["blobs"]["packs/desk-website-service-20260902-01/door.html"],
            "d3d6fcc7",
        )
        self.assertEqual(self.result["blobs"]["packs/waitlist.html"], "bdcaa7ea")
        self.assertEqual(
            self.result["blobs"]["host/business_pack_harborline_tally_map.py"],
            "2fbc987b",
        )
        self.assertEqual(
            self.result["blobs"]["p/cursor-pack-harborline-rating-20260902-01.md"],
            "29930d8b",
        )
        self.assertNotIn("write_text", self.helper)
        self.assertNotIn("337 NO", json.dumps(self.result))

    def test_receipt_is_unique_and_unread_peers(self) -> None:
        self.assertIn("id: grokbuild-harborline-keep-pin-match-20260902-01", self.receipt)
        self.assertIn("NOT_MINTED", self.receipt)
        self.assertIn("a7a49b77", self.receipt)
        self.assertIn("68b4fce1", self.receipt)
        self.assertIn("a889db44", self.receipt)
        self.assertIn("KEEP MAIN", self.receipt)
        self.assertIn("#7754", self.receipt)
        self.assertIn("did not remint", self.receipt.lower())
        self.assertIn("33676044465", self.receipt)
        self.assertNotEqual(
            self.receipt.split("id:", 1)[1].splitlines()[0].strip(),
            "grokbuild-tests-battery-never-say-opportunity-20260902-01",
        )

    def test_cli_json(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "grokbuild_harborline_keep_pin_match.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        self.assertTrue(data["match_ok"])
        self.assertEqual(data["id"], "grokbuild-harborline-keep-pin-match-20260902-01")
        self.assertEqual(data["kind"], "HARBORLINE_KEEP_PIN_MATCH")
        self.assertEqual(data["checkout"], "NOT_MINTED")
        self.assertIs(data["gate"], False)


if __name__ == "__main__":
    unittest.main()
