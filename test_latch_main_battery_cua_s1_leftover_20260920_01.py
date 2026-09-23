#!/usr/bin/env python3
"""latch-main-battery-cua-s1-leftover-20260920-01 — catalog waitlist land-time prefixes."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_instance_waitlist as waitlist  # noqa: E402
import business_pack_sidewalk_lotribbon_waitlist as sidewalk  # noqa: E402
import business_pack_sold_once_badge_pointer as sold_once  # noqa: E402
import business_pack_waitlist_pixel_gate_pointer as pixel  # noqa: E402

RECEIPT = ROOT / "p" / "latch-main-battery-cua-s1-leftover-20260920-01.md"
BASS = ROOT / "p" / "latch-bass-imagedrop-stripe-door-20260920-01.md"
GROK_SEAT = ROOT / "p" / "grok-seat-carry-work-20260920-01.md"
TESTS_YML = ROOT / ".github" / "workflows" / "tests.yml"
IMAGE_DROP = ROOT / "image-drop.html"
WHITE_BOX_HOUR = "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07"
HIST = ("b312ed6d", "638e60b4", "ac60db02", "a550ae1b", "76388c9a", "b3f26525")


def git_blob_prefix(rel: str) -> str:
    payload = (ROOT / rel).read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()[:8]


class TestLatchMainBatteryCuaS1Leftover2026092001(unittest.TestCase):
    def test_receipt_is_first_mint_and_does_not_remint_forbidden_ids(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: latch-main-battery-cua-s1-leftover-20260920-01", text)
        self.assertIn("CLAIM LATCH", text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("Did not remint `grok-seat-carry-work-20260920-01`", text)
        self.assertIn("test_business_pack_instance_waitlist.py", text)
        self.assertTrue(BASS.is_file())
        self.assertFalse(GROK_SEAT.exists())
        self.assertNotIn("337 NO", text)

    def test_bass_keep_still_holds_existing_white_box_hour_pl(self) -> None:
        html = IMAGE_DROP.read_text(encoding="utf-8")
        self.assertIn(WHITE_BOX_HOUR, html)
        self.assertEqual(html.count("buy.stripe.com"), 1)
        bass = (ROOT / "test_bass_doors_larger_fixed_20260916_01.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("image-drop.html", bass)
        self.assertIn("VERIFIED_PRODUCT_CHECKOUT", bass)
        self.assertIn(WHITE_BOX_HOUR, bass)

    def test_catalog_helpers_keep_land_time_prefixes_and_unpin_live_pages(self) -> None:
        result = waitlist.classify_catalog()
        self.assertEqual(waitlist.EXPECTED_BLOBS["packs/waitlist.html"], "b312ed6d")
        self.assertEqual(
            waitlist.OBSERVED_AT_LAND[
                "packs/sidewalk-signal-web-desk-20260902-01/index.html"
            ],
            "638e60b4",
        )
        self.assertEqual(
            waitlist.OBSERVED_AT_LAND["host/business_pack_desk_instance.py"],
            "a550ae1b",
        )
        self.assertEqual(
            sidewalk.OBSERVED_AT_LAND[
                "packs/lotribbon-greetings-20260902-01/index.html"
            ],
            "ac60db02",
        )
        self.assertEqual(
            sold_once.OBSERVED_AT_LAND[
                "packs/sidewalk-signal-web-desk-20260902-01/index.html"
            ],
            "638e60b4",
        )
        self.assertEqual(pixel.EXPECTED_BLOBS["packs/waitlist.html"], "b312ed6d")
        self.assertEqual(pixel.EXPECTED_BLOBS["packs/thanks.html"], "76388c9a")
        self.assertTrue(
            pixel.EXPECTED_BLOBS["host/pack_waitlist_pixel_gate_pointer.py"].startswith(
                "b3f26525"
            )
        )
        self.assertTrue(result["pointer_ok"])
        self.assertIs(result["live_instance_blobs_not_pinned"], True)
        live_waitlist = git_blob_prefix("packs/waitlist.html")
        self.assertTrue(live_waitlist)
        if live_waitlist != "b312ed6d":
            self.assertFalse(result["waitlist_blob_ok"])
        for prefix in HIST:
            kind = subprocess.check_output(
                ["git", "-C", str(ROOT), "cat-file", "-t", prefix],
                text=True,
            ).strip()
            self.assertEqual(kind, "blob", prefix)

    def test_hosted_battery_stays_fail_fast(self) -> None:
        workflow = TESTS_YML.read_text(encoding="utf-8")
        self.assertIn(
            'python3 host/ci_battery.py --fail-fast --results "$RUNNER_TEMP/commons-battery-results.nul"',
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
