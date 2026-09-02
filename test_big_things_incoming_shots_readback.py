#!/usr/bin/env python3
"""Pin unique-pack readback of incoming-shots leftover. Do not remint pixels."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-big-things-incoming-shots-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-big-things-incoming-shots-20260902-01.md"

KEEP = {
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "shots/cursor-big-things-incoming-hub-1-20260902.png": "ac761b70",
    "shots/cursor-big-things-incoming-hub-1-20260902.thumb.jpg": "2590f4ab",
    "shots/cursor-big-things-incoming-hub-2-20260902.png": "8eb5940f",
    "shots/cursor-big-things-incoming-hub-2-20260902.thumb.jpg": "214307de",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "ground/OWNER_NOW.md": "59b1fd37",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-incoming-models-hub-payload-readback-20260902-01.md": "2d297673",
    "p/cursor-big-things-incoming-alert-ack-20260902-01.md": "81097728",
    "autogtm.html": "9d8b3e85",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestBigThingsIncomingShotsReadback(unittest.TestCase):
    def test_keep_leftover_pixels_and_unique_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_big_things_incoming_shots.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-big-things-incoming-shots-readback-20260902-01", text)
        self.assertIn("0544eba21", text)
        self.assertIn("60b24eff", text)
        self.assertIn("Did not steal", text)
        self.assertIn("Did not spawn", text)
        self.assertIn("Did not remint leftover pixels", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
