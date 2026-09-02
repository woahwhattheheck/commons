#!/usr/bin/env python3
"""Pin unique-pack readback of Harborline /qualify live-probe leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/harborline_qualify_live_probe.py"
LEFTOVER = ROOT / "p/cursor-harborline-qualify-live-probe-20260902-01.md"
READBACK = ROOT / "p/cursor-harborline-qualify-live-probe-readback-20260902-01.md"

KEEP = {
    "host/harborline_qualify_live_probe.py": "2c1797b2",
    "test_harborline_qualify_live_probe.py": "0791b11a",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "autogtm.html": "9d8b3e85",
    "p/cursor-autogtm-door-live-probe-20260902-01.md": "c71c57a0",
    "p/cursor-explee-qualify-clone-20260902-01.md": "aceb4aead",
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md": "7a8987b5",
    "p/cursor-autogtm-explee-same-loop-20260902-01.md": "c437f4d6",
    "host/explee_autogtm_local.py": "5407261c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestHarborlineQualifyLiveProbeReadback(unittest.TestCase):
    def test_keep_leftover_and_unique_pack_door_exact(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = READBACK.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-qualify-live-probe-readback-20260902-01", text)
        self.assertIn("a83cba69a", text)
        self.assertIn("2c1797b2", text)
        self.assertIn("92c4e31f", text)
        self.assertIn("9d8b3e85", text)
        self.assertIn("Did not steal", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("Did not dump", text)
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("aceb4aead", leftover)
        self.assertNotEqual(text, leftover)

    def test_leftover_go_still_refused_sent_zero(self) -> None:
        proc = subprocess.run(
            ["python3", str(HELPER), "--go"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["booked"], 0)
        self.assertEqual(payload["cash"], 0)
        self.assertEqual(payload["refused"], "--go")

    def test_did_not_dump_qualify_html_or_corner(self) -> None:
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertTrue(HELPER.exists())


if __name__ == "__main__":
    unittest.main()
