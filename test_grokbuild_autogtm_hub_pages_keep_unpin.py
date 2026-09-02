#!/usr/bin/env python3
"""Lift ACK leftover KEEP freeze of hub_pages.py after live-GET remint."""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE_GET = "live GET /public/api/v1/autogtm/projects credentials=omit"
ACK_TEST = ROOT / "test_autogtm_door_hub_readback_ack.py"
ACK_RECEIPT = ROOT / "p/cursor-autogtm-door-hub-readback-ack-20260902-01.md"
UNPIN_RECEIPT = ROOT / "p/grokbuild-autogtm-hub-pages-keep-unpin-20260902-01.md"

KEEP_UNREAD = {
    "p/cursor-autogtm-door-hub-readback-ack-20260902-01.md": "292bc1a7",
    "p/cursor-autogtm-door-hub-readback-20260902-01.md": "8c7c170a",
    "p/cursor-autogtm-hub-pages-live-get-readback-ack-20260902-01.md": "a642d7d1",
    "p/cursor-autogtm-hub-pages-live-get-readback-20260902-01.md": "c2829fc5",
    "autogtm.html": "9d8b3e85",
    "door.js": "1f9e8d14",
    "hub_pages.py": "14eeedb0",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class GrokbuildAutogtmHubPagesKeepUnpinTest(unittest.TestCase):
    def test_ack_leftover_keep_does_not_freeze_hub_pages(self) -> None:
        import test_autogtm_door_hub_readback_ack as ack

        self.assertNotIn("hub_pages.py", ack.KEEP)
        self.assertNotIn("boards.html", ack.KEEP)
        self.assertNotIn("index.html", ack.KEEP)
        text = ACK_TEST.read_text(encoding="utf-8")
        self.assertNotIn("d0ec6161", text)

    def test_hub_still_names_autogtm_live_get(self) -> None:
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn('href="./autogtm.html">AutoGTM</a>', hub)
        self.assertIn("same loop as Explee", hub)
        self.assertIn(LIVE_GET, hub)
        self.assertIn(LIVE_GET, boards)
        page = (ROOT / "autogtm.html").read_text(encoding="utf-8")
        self.assertIn('credentials: "omit"', page)
        self.assertNotIn('type="password"', page)

    def test_did_not_remint_ack_receipts_or_later_leftover(self) -> None:
        for rel, prefix in KEEP_UNREAD.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        ack = ACK_RECEIPT.read_text(encoding="utf-8")
        self.assertIn("Did not remint", ack)
        self.assertIn("d0ec6161", ack)
        unpin = UNPIN_RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: grokbuild-autogtm-hub-pages-keep-unpin-20260902-01", unpin)
        self.assertIn("14eeedb0", unpin)
        self.assertIn("Did not remint", unpin)
        self.assertIn("#7915", unpin)
        self.assertIn("NOT_MINTED", unpin)


if __name__ == "__main__":
    unittest.main()
