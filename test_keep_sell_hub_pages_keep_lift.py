#!/usr/bin/env python3
"""KEEP-lift leftover hub_pages freeze after KEEP vs SELL board projection.

PR #11107 restored the canonical KEEP vs SELL row in hub_pages.rebuild_boards().
Leftover KEEP dicts had frozen hub_pages.py at 7a8f24d5 / boards.html at a44e8e3e,
so the discovered battery failed as a remint. This leftover MATCHES the live
blobs and does not remint leftover unique packs, AutoGTM, door.js, or receipts.
"""
from __future__ import annotations

import importlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HREF = 'href="./keep-sell.html"'
TITLE = ">KEEP vs SELL</a>"
COPY = "Factory classification ledger. Marketing stays Bryce. No invented Stripe URLs."
HUB_BLOB = "d0bd0e8d"
STALE_HUB = "7a8f24d5"
BOARDS_BLOB = "143730a0"
STALE_BOARDS = "a44e8e3e"

KEEP_UNREAD = {
    "autogtm.html": "fab1d536",
    "door.js": "0ef6caa0",
    "ground/OWNER_NOW.md": "0a574d94",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-pack-is-ready-to-run-20260902-01.md": "897b00ba",
    "test_keep_sell_board_projection.py": "48a06148",
}

KEEP_MODULES = (
    "test_commerce_agents",
    "test_commerce_agents_same_loop",
    "test_commons_slack_full_body",
    "test_cursor_goat_pages_super_mcp_land_readback",
    "test_stealable_lanes",
)


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class KeepSellHubPagesKeepLiftTest(unittest.TestCase):
    def test_leftover_keep_no_longer_freezes_stale_hub_or_boards(self) -> None:
        for name in KEEP_MODULES:
            mod = importlib.import_module(name)
            keep = getattr(mod, "KEEP", {})
            unread = getattr(mod, "KEEP_UNREAD", {})
            self.assertNotEqual(keep.get("hub_pages.py"), STALE_HUB, name)
            self.assertNotEqual(unread.get("hub_pages.py"), STALE_HUB, name)
            self.assertNotEqual(keep.get("boards.html"), STALE_BOARDS, name)
            if "hub_pages.py" in keep:
                self.assertEqual(keep["hub_pages.py"], HUB_BLOB, name)
            if "boards.html" in keep:
                self.assertEqual(keep["boards.html"], BOARDS_BLOB, name)

    def test_hub_and_boards_keep_sell_row_and_live_blobs(self) -> None:
        hub = git_blob("hub_pages.py")
        boards = git_blob("boards.html")
        self.assertTrue(hub.startswith(HUB_BLOB), hub)
        self.assertFalse(hub.startswith(STALE_HUB), hub)
        self.assertTrue(boards.startswith(BOARDS_BLOB), boards)
        self.assertFalse(boards.startswith(STALE_BOARDS), boards)
        hub_text = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        board_text = (ROOT / "boards.html").read_text(encoding="utf-8")
        for text in (hub_text, board_text):
            self.assertIn(HREF, text)
            self.assertIn(TITLE, text)
            self.assertIn(COPY, text)
            self.assertEqual(text.count(HREF), 1)
            self.assertLess(text.index('href="./payment-capability.html"'), text.index(HREF))
            self.assertLess(text.index(HREF), text.index('href="./look.html"'))
        self.assertIn('href="./autogtm.html">AutoGTM</a>', hub_text)

    def test_did_not_remint_leftover_unique_packs(self) -> None:
        for rel, prefix in KEEP_UNREAD.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_projection_and_commerce_leftover_now_pass(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_keep_sell_board_projection.py",
                "test_commerce_agents.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        combined = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, msg=combined)
        self.assertNotIn(f"hub_pages.py reminted: want {STALE_HUB}", combined)


if __name__ == "__main__":
    unittest.main()
