#!/usr/bin/env python3
"""Pin unique-pack hub readback MATCH; KEEP leftover ACK and door.js."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

KEEP = {
    "p/cursor-autogtm-door-hub-readback-20260902-01.md": "8c7c170a",
    "p/cursor-autogtm-peer-readback-ack-20260902-01.md": "d9d1008e",
    "door.js": "1f9e8d14",
    "autogtm.html": "9d8b3e85",
    "test_autogtm_door_hub.py": "fef0303e",
    "hub_pages.py": "d0ec6161",
    "p/cursor-autogtm-door-live-probe-20260902-01.md": "c71c57a0",
    "p/cursor-autogtm-explee-same-loop-20260902-01.md": "c437f4d6",
    "p/cursor-explee-qualify-clone-20260902-01.md": "aceb4aead",
    "p/cursor-explee-skills-adopt-20260902-01.md": "20db155c",
    "host/explee_autogtm_local.py": "5407261c",
    "p/cursor-autogtm-peer-ack-lead-landed-20260902-01.md": "68fa5493",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestAutogtmDoorHubReadbackAck(unittest.TestCase):
    def test_keep_main_unique_paths_exact(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_ack_receipt_exists_and_does_not_steal(self) -> None:
        ack = (
            ROOT / "p/cursor-autogtm-door-hub-readback-ack-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.assertIn("8c7c170a", ack)
        self.assertIn("1f9e8d14", ack)
        self.assertIn("9d8b3e85", ack)
        self.assertIn("6bd16532c", ack)
        self.assertIn("d9d1008e", ack)
        self.assertIn("aceb4aead", ack)
        self.assertIn("20db155c", ack)
        self.assertIn("Did not steal", ack)
        self.assertIn("Sheshiyer", ack)
        self.assertNotIn("qualify.html", ack)

    def test_hub_still_surfaces_autogtm_without_remint(self) -> None:
        door = (ROOT / "door.js").read_text(encoding="utf-8")
        self.assertIn('["autogtm.html", "AutoGTM"]', door)
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="./autogtm.html">AutoGTM</a>', index)
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn('href="./autogtm.html">AutoGTM</a>', boards)
        self.assertIn("same loop as Explee", boards)
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertIn('href="./autogtm.html">AutoGTM</a>', hub)
        self.assertIn("same loop as Explee", hub)
        page = (ROOT / "autogtm.html").read_text(encoding="utf-8")
        self.assertIn('credentials: "omit"', page)
        self.assertNotIn('type="password"', page)
        self.assertNotIn("qualify.html", page)

    def test_keep_does_not_freeze_fat_ingest_blobs(self) -> None:
        self.assertNotIn("boards.html", KEEP)
        self.assertNotIn("index.html", KEEP)


if __name__ == "__main__":
    unittest.main()
