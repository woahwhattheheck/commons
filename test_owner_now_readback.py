#!/usr/bin/env python3
"""Pin unique-pack readback of OWNER_NOW spoken-rules leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARD = ROOT / "ground/OWNER_NOW.md"
RECEIPT = ROOT / "p/cursor-owner-now-readback-20260902-01.md"

KEEP = {
        "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "autogtm.html": "9d8b3e85",
    "hub_pages.py": "14eeedb0",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-autogtm-hub-pages-live-get-readback-20260902-01.md": "c2829fc5",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestOwnerNowReadback(unittest.TestCase):
    def test_keep_owner_now_and_unique_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_owner_now_in_force_is_generate_revenue(self) -> None:
        text = CARD.read_text(encoding="utf-8")
        self.assertIn("Point is generate revenue", text)
        self.assertIn("Stop zero-cash signoffs and integrity theater", text)
        self.assertIn("Do not invent fake URLs", text)
        self.assertIn("Mint real Stripe Payment Links when it helps", text)
        self.assertIn("invented 337 closer was never Bryce law", text)
        self.assertIn("Hourly reports are useful", text)
        self.assertIn("## Retired (peer virus, never owner law)", text)
        self.assertIn("NOT_MINTED as a freeze", text)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-owner-now-readback-20260902-01", text)
        self.assertIn("d12c231a8", text)
        self.assertIn("6b8ee988", text)
        self.assertIn("Did not steal", text)
        self.assertIn("Did not invent Stripe URLs", text)
        self.assertIn("Did not spawn", text)
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
