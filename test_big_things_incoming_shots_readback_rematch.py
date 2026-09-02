#!/usr/bin/env python3
"""Later-main rematch of unique-pack leftover incoming-shots readback."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-big-things-incoming-shots-readback-rematch-20260902-01.md"
UNIQUE_PACK = ROOT / "p/cursor-big-things-incoming-shots-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-big-things-incoming-shots-20260902-01.md"
SHOT1 = ROOT / "shots/cursor-big-things-incoming-hub-1-20260902.png"
SHOT2 = ROOT / "shots/cursor-big-things-incoming-hub-2-20260902.png"
THUMB1 = ROOT / "shots/cursor-big-things-incoming-hub-1-20260902.thumb.jpg"
THUMB2 = ROOT / "shots/cursor-big-things-incoming-hub-2-20260902.thumb.jpg"

KEEP = {
    "p/cursor-big-things-incoming-shots-readback-20260902-01.md": "3cabb764",
    "test_big_things_incoming_shots_readback.py": "1f6364be",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "test_big_things_incoming_shots.py": "1499b566",
    "shots/cursor-big-things-incoming-hub-1-20260902.png": "ac761b70",
    "shots/cursor-big-things-incoming-hub-1-20260902.thumb.jpg": "2590f4ab",
    "shots/cursor-big-things-incoming-hub-2-20260902.png": "8eb5940f",
    "shots/cursor-big-things-incoming-hub-2-20260902.thumb.jpg": "214307de",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-big-things-incoming-alert-ack-20260902-01.md": "81097728",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-incoming-models-hub-payload-readback-20260902-01.md": "2d297673",
    "p/cursor-incoming-models-hub-payload-readback-rematch-20260902-01.md": "c6707847",
    "ground/OWNER_NOW.md": "6b8ee988",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "autogtm.html": "9d8b3e85",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "test_harborline_pack_market_render.py": "e8f8703c",
    "p/cursor-harborline-pack-market-render-readback-20260902-01.md": "6efbac54",
    "p/cursor-harborline-pack-market-slack-render-20260902-01.md": "0d95f2ab",
    "host/harborline_pack_market_slack_render.py": "a03534da",
    "test_harborline_pack_market_slack_render.py": "23a840b5",
    "p/cursor-big-things-incoming-shots-readback-ack-20260902-01.md": "6311eee5",
    "test_big_things_incoming_shots_readback_ack.py": "1f104c66",
    "p/cursor-harborline-pack-market-render-readback-rematch-20260902-01.md": "f965e00f",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestBigThingsIncomingShotsReadbackRematch(unittest.TestCase):
    def test_keep_leftover_pixels_and_unique_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_tests_fail_only_on_hub_pages_remint(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_big_things_incoming_shots.py",
                "test_big_things_incoming_shots_readback.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        combined = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, msg=combined)
        self.assertIn("hub_pages.py reminted: want 14eeedb0 got 5ac12648", combined)
        self.assertNotIn("shots/cursor-big-things-incoming-hub-1-20260902.png reminted", combined)
        self.assertNotIn("60b24eff reminted", combined)
        self.assertNotIn("3cabb764 reminted", combined)

    def test_owner_shots_still_the_leftover_pixels(self) -> None:
        for path in (SHOT1, SHOT2, THUMB1, THUMB2):
            self.assertTrue(path.is_file(), f"missing {path.name}")
        self.assertEqual(SHOT1.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(SHOT2.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(THUMB1.read_bytes()[:3], b"\xff\xd8\xff")
        self.assertEqual(THUMB2.read_bytes()[:3], b"\xff\xd8\xff")

    def test_ack_leftover_post_kept_after_peer_unpin(self) -> None:
        ack_post = git_blob("p/cursor-big-things-incoming-shots-readback-ack-20260902-01.md")
        unique_pack = git_blob("p/cursor-big-things-incoming-shots-readback-20260902-01.md")
        leftover = git_blob("p/cursor-big-things-incoming-shots-20260902-01.md")
        ack_test = git_blob("test_big_things_incoming_shots_readback_ack.py")
        self.assertTrue(ack_post.startswith("6311eee5"), ack_post)
        self.assertTrue(unique_pack.startswith("3cabb764"), unique_pack)
        self.assertTrue(leftover.startswith("60b24eff"), leftover)
        self.assertTrue(ack_test.startswith("1f104c66"), ack_test)
        self.assertFalse(ack_test.startswith("a9cc500d"), ack_test)

    def test_rematch_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        unique_pack = UNIQUE_PACK.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-big-things-incoming-shots-readback-rematch-20260902-01", text)
        self.assertIn("c57e501b1", text)
        self.assertIn("3cabb764", text)
        self.assertIn("60b24eff", text)
        self.assertIn("Did not remint leftover pixels", text)
        self.assertIn("Did not spawn", text)
        self.assertIn("Did not steal Harborline `/harborline`", text)
        self.assertIn("hub_pages.py reminted: want 14eeedb0 got 5ac12648", text)
        self.assertIn("0918db368", text)
        self.assertIn("6311eee5", text)
        self.assertNotEqual(text, unique_pack)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "harborline.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
