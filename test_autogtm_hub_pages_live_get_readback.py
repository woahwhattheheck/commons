#!/usr/bin/env python3
"""Pin unique-pack readback of AutoGTM hub_pages live-GET leftover (#8330)."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-autogtm-hub-pages-live-get-readback-20260902-01.md"
LIVE_GET = "live GET /public/api/v1/autogtm/projects credentials=omit"

KEEP = {
    "hub_pages.py": "14eeedb0",
    "test_autogtm_peer_readback_ack.py": "a9569288",
    "autogtm.html": "9d8b3e85",
    "door.js": "1f9e8d14",
    "p/cursor-autogtm-door-live-probe-20260902-01.md": "c71c57a0",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "host/harborline_qualify_live_probe.py": "2c1797b2",
    "p/cursor-harborline-qualify-live-probe-readback-20260902-01.md": "c2532b3d",
    "p/cursor-pr7915-closed-unmerged-readback-20260902-01.md": "2a7f31a4",
    "p/cursor-explee-skills-adopt-20260902-01.md": "20db155c",
    "host/explee_autogtm_local.py": "5407261c",
    "p/cursor-autogtm-explee-same-loop-20260902-01.md": "c437f4d6",
    "p/cursor-autogtm-door-hub-readback-20260902-01.md": "8c7c170a",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestAutogtmHubPagesLiveGetReadback(unittest.TestCase):
    def test_keep_leftover_generator_and_unique_pack_door(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_generator_and_boards_name_live_get(self) -> None:
        gen = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn(LIVE_GET, gen)
        self.assertIn(LIVE_GET, boards)
        self.assertIn('href="./autogtm.html"', boards)
        door = (ROOT / "autogtm.html").read_text(encoding="utf-8")
        self.assertIn('credentials: "omit"', door)
        self.assertNotIn("qualify.html", door)
        self.assertNotIn("qualify.html", gen)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-autogtm-hub-pages-live-get-readback-20260902-01", text)
        self.assertIn("930903572", text)
        self.assertIn("3d821da1a", text)
        self.assertIn("14eeedb0", text)
        self.assertIn("9d8b3e85", text)
        self.assertIn("Did not steal", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
