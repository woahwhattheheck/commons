#!/usr/bin/env python3
"""Pin unique ACK of unique-pack #7915 + Harborline live-probe readbacks."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACK = ROOT / "p/cursor-pr7915-harborline-readbacks-ack-20260902-01.md"
HELPER = ROOT / "host/pr7915_closed_unmerged.py"

KEEP = {
    "p/cursor-pr7915-closed-unmerged-readback-20260902-01.md": "2a7f31a4",
    "p/cursor-harborline-qualify-live-probe-readback-20260902-01.md": "c2532b3d",
    "host/pr7915_closed_unmerged.py": "9d56ea0e",
    "test_pr7915_closed_unmerged.py": "6f0178ab",
    "test_harborline_qualify_live_probe_readback.py": "014c1862",
    "host/harborline_qualify_live_probe.py": "2c1797b2",
    "test_harborline_qualify_live_probe.py": "0791b11a",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "autogtm.html": "9d8b3e85",
    "p/cursor-autogtm-door-live-probe-20260902-01.md": "c71c57a0",
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md": "7a8987b5",
    "p/cursor-explee-qualify-clone-20260902-01.md": "aceb4aead",
    "p/cursor-explee-skills-adopt-20260902-01.md": "20db155c",
    "host/explee_autogtm_local.py": "5407261c",
    "p/cursor-autogtm-explee-same-loop-20260902-01.md": "c437f4d6",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestPr7915HarborlineReadbacksAck(unittest.TestCase):
    def test_keep_main_unique_paths_exact(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_ack_receipt_exists_and_does_not_steal(self) -> None:
        text = ACK.read_text(encoding="utf-8")
        self.assertIn("cursor-pr7915-harborline-readbacks-ack-20260902-01", text)
        self.assertIn("2a7f31a4", text)
        self.assertIn("c2532b3d", text)
        self.assertIn("92c4e31f", text)
        self.assertIn("2c1797b2", text)
        self.assertIn("7a8987b5", text)
        self.assertIn("9d8b3e85", text)
        self.assertIn("fa046ce05900", text)
        self.assertIn("19:44:19Z", text)
        self.assertIn("ec7fd9142", text)
        self.assertIn("a83cba69a", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not steal", text)
        self.assertIn("Sheshiyer", text)
        self.assertIn("Did not dump", text)
        self.assertNotIn("qualify.html", text)

    def test_reopen_merge_go_still_refused_sent_zero(self) -> None:
        for flag in ("--reopen", "--merge", "--go"):
            proc = subprocess.run(
                ["python3", str(HELPER), flag],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["state"], "REFUSED")
            self.assertEqual(payload["sent"], 0)
            self.assertFalse(payload["reopened"])
            self.assertFalse(payload["merged"])

    def test_did_not_dump_qualify_html_or_corner(self) -> None:
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertTrue(ACK.exists())

    def test_keep_does_not_freeze_fat_ingest_blobs(self) -> None:
        self.assertNotIn("boards.html", KEEP)
        self.assertNotIn("index.html", KEEP)
        self.assertNotIn("hub_pages.py", KEEP)
        self.assertNotIn("door.js", KEEP)


if __name__ == "__main__":
    unittest.main()
