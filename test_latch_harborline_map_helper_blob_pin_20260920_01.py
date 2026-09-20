#!/usr/bin/env python3
"""latch-harborline-map-helper-blob-pin-20260920-01 — RECEIPT pins match; keep historical EXPECTED."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_harborline_map_helper_pointer as pointer  # noqa: E402

RECEIPT = ROOT / "p" / "latch-harborline-map-helper-blob-pin-20260920-01.md"
POINTER = (
    ROOT / "p" / "cursor-business-pack-harborline-map-helper-pointer-20260902-01.md"
)
HELPER = ROOT / "host" / "business_pack_harborline_map_helper_pointer.py"
MAP_HELPER = ROOT / "host" / "harborline_tally_pack_map.py"
DOOR = ROOT / "packs" / "desk-website-service-20260902-01" / "door.html"
WAITLIST = ROOT / "packs" / "waitlist.html"
GROK_SEAT = ROOT / "p" / "grok-seat-carry-work-20260920-01.md"
NAMED_TEST = ROOT / "test_business_pack_harborline_map_helper_pointer.py"

POINTER_PIN = "269e874a"
SIDEWALK_PIN = "2c584983"
MAP_PIN = "a7a49b77"
HIST_DOOR = "299b01fd"
HIST_WAITLIST = "211db2dc"
DO_NOT_WRITE = (
    "host/harborline_tally_pack_map.py",
    "packs/desk-website-service-20260902-01/door.html",
    "packs/waitlist.html",
    "p/cursor-business-pack-harborline-map-helper-pointer-20260902-01.md",
    "p/cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01.md",
    "host/business_pack_harborline_map_helper_pointer.py",
)


def git_blob_prefix(rel: str) -> str:
    payload = (ROOT / rel).read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()[:8]


def git_blob_full(rel: str) -> str:
    payload = (ROOT / rel).read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()


class TestLatchHarborlineMapHelperBlobPin2026092001(unittest.TestCase):
    def test_receipt_is_first_mint_and_does_not_remint_forbidden_ids(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: latch-harborline-map-helper-blob-pin-20260920-01", text)
        self.assertIn("CLAIM LATCH", text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("Did not remint `grok-seat-carry-work-20260920-01`", text)
        self.assertIn(
            "Did not remint `cursor-business-pack-harborline-map-helper-pointer-20260902-01`",
            text,
        )
        self.assertIn("KEEP MAIN #7754", text)
        self.assertIn(SIDEWALK_PIN, text)
        self.assertFalse(GROK_SEAT.exists())
        self.assertNotIn("337 NO", text)
        self.assertNotIn("cash=$0", text.lower())

    def test_recomputed_receipt_blobs_match_current_pins(self) -> None:
        for rel, pin in pointer.RECEIPT_BLOBS.items():
            live = git_blob_prefix(rel)
            self.assertEqual(live, pin, rel)
            self.assertEqual(live, pointer.blob_prefix(rel), rel)
        self.assertEqual(
            pointer.RECEIPT_BLOBS[
                "p/cursor-business-pack-harborline-map-helper-pointer-20260902-01.md"
            ],
            POINTER_PIN,
        )
        self.assertEqual(
            pointer.RECEIPT_BLOBS[
                "p/cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01.md"
            ],
            SIDEWALK_PIN,
        )
        self.assertTrue(
            git_blob_full(
                "p/cursor-business-pack-harborline-map-helper-pointer-20260902-01.md"
            ).startswith(POINTER_PIN)
        )
        self.assertTrue(
            git_blob_full(
                "p/cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01.md"
            ).startswith(SIDEWALK_PIN)
        )
        result = pointer.classify_pointer()
        self.assertTrue(result["receipt_blobs_match"])
        self.assertTrue(result["keep_main"])
        self.assertTrue(result["pointer_ok"])
        self.assertEqual(result["keep_main_pr"], 7754)
        self.assertEqual(result["original_sidewalk_lotribbon_receipt"], SIDEWALK_PIN)
        self.assertIs(result["live_instance_blobs_not_pinned"], True)

    def test_historical_expected_door_waitlist_stay_unlifted(self) -> None:
        self.assertEqual(
            pointer.EXPECTED_BLOBS["packs/desk-website-service-20260902-01/door.html"],
            HIST_DOOR,
        )
        self.assertEqual(pointer.EXPECTED_BLOBS["packs/waitlist.html"], HIST_WAITLIST)
        self.assertEqual(
            pointer.EXPECTED_BLOBS["host/harborline_tally_pack_map.py"], MAP_PIN
        )
        self.assertEqual(
            git_blob_prefix("host/harborline_tally_pack_map.py"), MAP_PIN
        )
        live_door = git_blob_prefix(
            "packs/desk-website-service-20260902-01/door.html"
        )
        live_waitlist = git_blob_prefix("packs/waitlist.html")
        self.assertTrue(live_door)
        self.assertTrue(live_waitlist)
        result = pointer.classify_pointer()
        if live_door != HIST_DOOR or live_waitlist != HIST_WAITLIST:
            self.assertFalse(result["blobs_match"])
        named = NAMED_TEST.read_text(encoding="utf-8")
        self.assertIn('startswith(\n                "299b01fd"', named)
        self.assertIn('startswith("211db2dc")', named)
        for prefix in (HIST_DOOR, HIST_WAITLIST, POINTER_PIN, SIDEWALK_PIN, MAP_PIN):
            kind = subprocess.check_output(
                ["git", "-C", str(ROOT), "cat-file", "-t", prefix],
                text=True,
            ).strip()
            self.assertEqual(kind, "blob", prefix)

    def test_did_not_overwrite_map_helper_doors_waitlist_or_pointer(self) -> None:
        pointer_text = POINTER.read_text(encoding="utf-8")
        self.assertIn(
            "id: cursor-business-pack-harborline-map-helper-pointer-20260902-01",
            pointer_text,
        )
        self.assertIn("KEEP MAIN", pointer_text)
        self.assertIn("#7754", pointer_text)
        self.assertIn(SIDEWALK_PIN, pointer_text)
        helper_text = HELPER.read_text(encoding="utf-8")
        self.assertIn(f'"{MAP_PIN}"', helper_text)
        self.assertIn(f'"{HIST_DOOR}"', helper_text)
        self.assertIn(f'"{HIST_WAITLIST}"', helper_text)
        self.assertIn(f'"{POINTER_PIN}"', helper_text)
        self.assertIn(f'"{SIDEWALK_PIN}"', helper_text)
        self.assertTrue(MAP_HELPER.is_file())
        self.assertTrue(DOOR.is_file())
        self.assertTrue(WAITLIST.is_file())
        dirty = subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--"] + list(DO_NOT_WRITE),
            text=True,
        )
        self.assertEqual(dirty.strip(), "")

    def test_named_helper_unittest_stays_green(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "-q",
                "test_business_pack_harborline_map_helper_pointer",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("Ran 6 tests", proc.stderr)


if __name__ == "__main__":
    unittest.main()
