#!/usr/bin/env python3
"""Pin unique ACK of unique-pack hub_pages live-GET leftover. Do not remint."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACK = ROOT / "p/cursor-autogtm-hub-pages-live-get-readback-ack-20260902-01.md"
LIVE_GET = "live GET /public/api/v1/autogtm/projects credentials=omit"

KEEP = {
    "p/cursor-autogtm-hub-pages-live-get-readback-20260902-01.md": "c2829fc5",
    "autogtm.html": "9d8b3e85",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "host/harborline_qualify_live_probe.py": "2c1797b2",
    "test_harborline_qualify_live_probe.py": "0791b11a",
    "p/cursor-harborline-qualify-live-probe-readback-20260902-01.md": "c2532b3d",
    "p/cursor-pr7915-closed-unmerged-readback-20260902-01.md": "2a7f31a4",
    "p/cursor-autogtm-door-live-probe-20260902-01.md": "c71c57a0",
    "p/cursor-explee-skills-adopt-20260902-01.md": "20db155c",
    "host/explee_autogtm_local.py": "5407261c",
    "p/cursor-autogtm-explee-same-loop-20260902-01.md": "c437f4d6",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestAutogtmHubPagesLiveGetReadbackAck(unittest.TestCase):
    def test_keep_main_unique_paths_exact(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_ack_receipt_exists_and_does_not_steal(self) -> None:
        text = ACK.read_text(encoding="utf-8")
        self.assertIn("cursor-autogtm-hub-pages-live-get-readback-ack-20260902-01", text)
        self.assertIn("c2829fc5", text)
        self.assertIn("14eeedb0", text)
        self.assertIn("930903572", text)
        self.assertIn("3d821da1a", text)
        self.assertIn("ad7bc7a40", text)
        self.assertIn("9d8b3e85", text)
        self.assertIn("92c4e31f", text)
        self.assertIn("2c1797b2", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not steal", text)
        self.assertIn("Sheshiyer", text)
        self.assertNotIn("qualify.html", text)

    def test_generator_still_names_live_get_without_remint(self) -> None:
        gen = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn(LIVE_GET, gen)
        self.assertIn(LIVE_GET, boards)
        door = (ROOT / "autogtm.html").read_text(encoding="utf-8")
        self.assertIn('credentials: "omit"', door)
        self.assertNotIn('type="password"', door)
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())

    def test_keep_does_not_freeze_fat_ingest_boards(self) -> None:
        self.assertNotIn("boards.html", KEEP)
        self.assertNotIn("index.html", KEEP)


if __name__ == "__main__":
    unittest.main()
