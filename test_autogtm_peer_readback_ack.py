#!/usr/bin/env python3
"""Pin unique-pack readback + live-probe KEEP; boards names live GET."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

KEEP = {
    "p/cursor-autogtm-peer-ack-lead-landed-readback-20260902-01.md": "d3be87c2",
    "p/cursor-autogtm-peer-ack-lead-landed-20260902-01.md": "68fa5493",
    "p/cursor-autogtm-door-live-probe-20260902-01.md": "c71c57a0",
    "autogtm.html": "9d8b3e85",
    "p/cursor-explee-skills-adopt-20260902-01.md": "20db155c",
    "host/explee_autogtm_local.py": "5407261c",
    "p/cursor-explee-skills-adopt-readback-20260902-01.md": "33a78379",
    "p/cursor-autogtm-explee-same-loop-20260902-01.md": "c437f4d6",
    "p/cursor-autogtm-compose-door-wire-20260902-01.md": "b89fc352",
    "p/cursor-autogtm-ack-peers-20260902-01.md": "9de320f2",
    "p/cursor-explee-qualify-clone-20260902-01.md": "aceb4aead",
    "test_autogtm_same_loop.py": "70b8413e",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestAutogtmPeerReadbackAck(unittest.TestCase):
    def test_keep_main_unique_paths_exact(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_ack_receipt_exists_and_does_not_steal(self) -> None:
        ack = (ROOT / "p/cursor-autogtm-peer-readback-ack-20260902-01.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("d3be87c2", ack)
        self.assertIn("c71c57a0", ack)
        self.assertIn("68fa5493", ack)
        self.assertIn("aceb4aead", ack)
        self.assertIn("20db155c", ack)
        self.assertIn("Did not steal", ack)
        self.assertIn("Sheshiyer", ack)
        self.assertNotIn("qualify.html", ack)

    def test_boards_names_live_get(self) -> None:
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn('href="./autogtm.html"', boards)
        self.assertIn("same loop as Explee", boards)
        self.assertIn(
            "live GET /public/api/v1/autogtm/projects credentials=omit", boards
        )
        door = (ROOT / "autogtm.html").read_text(encoding="utf-8")
        self.assertIn('credentials: "omit"', door)
        self.assertNotIn("qualify.html", door)


if __name__ == "__main__":
    unittest.main()
