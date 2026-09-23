#!/usr/bin/env python3
"""latch-harborline-map-helper-blob-pin-20260920-02 — named test door/waitlist live prefixes."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_harborline_map_helper_pointer as pointer  # noqa: E402

RECEIPT = ROOT / "p" / "latch-harborline-map-helper-blob-pin-20260920-02.md"
PRIOR = ROOT / "p" / "latch-harborline-map-helper-blob-pin-20260920-01.md"
POINTER = (
    ROOT / "p" / "cursor-business-pack-harborline-map-helper-pointer-20260902-01.md"
)
NAMED = ROOT / "test_business_pack_harborline_map_helper_pointer.py"
GROK_SEAT = ROOT / "p" / "grok-seat-carry-work-20260920-01.md"
LIVE_DOOR = "d75b3f3b"
LIVE_WAITLIST = "f93c8f32"
POINTER_PIN = "269e874a"
SIDEWALK_PIN = "2c584983"


def git_blob_prefix(rel: str) -> str:
    payload = (ROOT / rel).read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()[:8]


class TestLatchHarborlineMapHelperBlobPin2026092002(unittest.TestCase):
    def test_receipt_is_first_mint_and_does_not_remint_forbidden_ids(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: latch-harborline-map-helper-blob-pin-20260920-02", text)
        self.assertIn("CLAIM LATCH", text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("Did not remint `latch-harborline-map-helper-blob-pin-20260920-01`", text)
        self.assertIn("Did not remint `grok-seat-carry-work-20260920-01`", text)
        self.assertIn(
            "Did not remint `cursor-business-pack-harborline-map-helper-pointer-20260902-01`",
            text,
        )
        self.assertTrue(PRIOR.is_file())
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("id: latch-harborline-map-helper-blob-pin-20260920-01", prior)
        self.assertFalse(GROK_SEAT.exists())
        self.assertNotIn("337 NO", text)
        self.assertNotIn("cash=$0", text.lower())

    def test_named_test_and_expected_blobs_use_live_door_waitlist_prefixes(self) -> None:
        named = NAMED.read_text(encoding="utf-8")
        self.assertIn('startswith(\n                "d75b3f3b"', named)
        self.assertIn('startswith("f93c8f32")', named)
        self.assertNotIn("299b01fd", named)
        self.assertNotIn("211db2dc", named)
        self.assertEqual(
            pointer.EXPECTED_BLOBS["packs/desk-website-service-20260902-01/door.html"],
            LIVE_DOOR,
        )
        self.assertEqual(pointer.EXPECTED_BLOBS["packs/waitlist.html"], LIVE_WAITLIST)
        self.assertEqual(
            git_blob_prefix("packs/desk-website-service-20260902-01/door.html"),
            LIVE_DOOR,
        )
        self.assertEqual(git_blob_prefix("packs/waitlist.html"), LIVE_WAITLIST)
        self.assertEqual(
            git_blob_prefix(
                "p/cursor-business-pack-harborline-map-helper-pointer-20260902-01.md"
            ),
            POINTER_PIN,
        )
        self.assertEqual(
            git_blob_prefix(
                "p/cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01.md"
            ),
            SIDEWALK_PIN,
        )
        pointer_text = POINTER.read_text(encoding="utf-8")
        self.assertIn(
            "id: cursor-business-pack-harborline-map-helper-pointer-20260902-01",
            pointer_text,
        )
        result = pointer.classify_pointer()
        self.assertTrue(result["receipt_blobs_match"])
        self.assertTrue(result["pointer_ok"])
        self.assertTrue(result["keep_main"])

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
