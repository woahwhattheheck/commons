#!/usr/bin/env python3
"""Pin independent ACK of shots-readback unique-pack. Do not remint pixels."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACK = ROOT / "p/cursor-big-things-incoming-shots-readback-ack-20260902-01.md"
UNIQUE = ROOT / "p/cursor-big-things-incoming-shots-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-big-things-incoming-shots-20260902-01.md"

KEEP = {
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "test_big_things_incoming_shots.py": "987f7350",
    "p/cursor-big-things-incoming-shots-readback-20260902-01.md": "3cabb764",
    "test_big_things_incoming_shots_readback.py": "7c4db09b",
    "shots/cursor-big-things-incoming-hub-1-20260902.png": "ac761b70",
    "shots/cursor-big-things-incoming-hub-1-20260902.thumb.jpg": "2590f4ab",
    "shots/cursor-big-things-incoming-hub-2-20260902.png": "8eb5940f",
    "shots/cursor-big-things-incoming-hub-2-20260902.thumb.jpg": "214307de",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-incoming-models-hub-payload-readback-20260902-01.md": "2d297673",
    "ground/OWNER_NOW.md": "59b1fd37",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-big-things-incoming-alert-ack-20260902-01.md": "81097728",
    "autogtm.html": "9d8b3e85",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestBigThingsIncomingShotsReadbackAck(unittest.TestCase):
    def test_keep_leftover_pixels_and_unique_pack(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_pixels_still_present(self) -> None:
        for rel in (
            "shots/cursor-big-things-incoming-hub-1-20260902.png",
            "shots/cursor-big-things-incoming-hub-2-20260902.png",
            "p/cursor-big-things-incoming-shots-20260902-01.md",
            "p/cursor-big-things-incoming-shots-readback-20260902-01.md",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)
        leftover = (ROOT / "p/cursor-big-things-incoming-shots-20260902-01.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Did not invent", leftover)
        self.assertIn("generate revenue", leftover)
        self.assertNotIn("buy.stripe.com", leftover)

    def test_ack_cites_unique_pack_without_reminting(self) -> None:
        text = ACK.read_text(encoding="utf-8")
        unique = UNIQUE.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn(
            "cursor-big-things-incoming-shots-readback-ack-20260902-01", text
        )
        self.assertIn(
            "cursor-big-things-incoming-shots-readback-20260902-01", text
        )
        self.assertIn("c57e501b1", text)
        self.assertIn("0544eba21", text)
        self.assertIn("60b24eff", text)
        self.assertIn("3cabb764", text)
        self.assertIn("Did not remint leftover pixels", text)
        self.assertIn("Did not invent a SKU", text)
        self.assertIn("Did not spawn", text)
        self.assertIn("Did not steal", text)
        self.assertIn("bc-b0b8882f", text)
        self.assertIn("1788380844.707619", text)
        self.assertNotEqual(text, unique)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(
            git_blob(
                "p/cursor-big-things-incoming-shots-readback-ack-20260902-01.md"
            ),
            git_blob(
                "p/cursor-big-things-incoming-shots-readback-20260902-01.md"
            ),
        )
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("qualify.html", text)
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
