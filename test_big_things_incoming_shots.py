#!/usr/bin/env python3
"""Pin unique hub-screenshot leftover. Do not remint the peer alert."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT / "p/cursor-big-things-incoming-alert-20260902-01.md"
RECEIPT = ROOT / "p/cursor-big-things-incoming-shots-20260902-01.md"
SHOT1 = ROOT / "shots/cursor-big-things-incoming-hub-1-20260902.png"
SHOT2 = ROOT / "shots/cursor-big-things-incoming-hub-2-20260902.png"
THUMB1 = ROOT / "shots/cursor-big-things-incoming-hub-1-20260902.thumb.jpg"
THUMB2 = ROOT / "shots/cursor-big-things-incoming-hub-2-20260902.thumb.jpg"

KEEP = {
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-big-things-incoming-alert-ack-20260902-01.md": "81097728",
    "autogtm.html": "9d8b3e85",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestBigThingsIncomingShots(unittest.TestCase):
    def test_keep_parent_alert_and_autogtm_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_shots_receipt_cites_parent_and_hub_line(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-big-things-incoming-shots-20260902-01", text)
        self.assertIn("cursor-big-things-incoming-alert-20260902-01", text)
        self.assertIn("1788380844.707619", text)
        self.assertIn("Big things incoming alert the peers", text)
        self.assertIn("Did not invent", text)
        self.assertIn("6b8ee988", text)
        self.assertIn("generate revenue", text)
        self.assertIn("Did not spawn", text)
        self.assertIn("image: shots/cursor-big-things-incoming-hub-1-20260902.png", text)
        self.assertIn("shots/cursor-big-things-incoming-hub-2-20260902.png", text)
        self.assertNotIn("qualify.html", text)
        self.assertNotIn("buy.stripe.com", text)

    def test_owner_shots_exist(self) -> None:
        for path in (SHOT1, SHOT2, THUMB1, THUMB2):
            self.assertTrue(path.is_file(), f"missing {path.name}")
            self.assertGreater(path.stat().st_size, 100)
        self.assertEqual(SHOT1.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(SHOT2.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(THUMB1.read_bytes()[:3], b"\xff\xd8\xff")
        self.assertEqual(THUMB2.read_bytes()[:3], b"\xff\xd8\xff")

    def test_did_not_dump_qualify_html_or_corner(self) -> None:
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
