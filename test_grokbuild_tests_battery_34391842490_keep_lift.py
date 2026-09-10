#!/usr/bin/env python3
"""Close leftover living hub/autogtm pins after tests battery 34391842490.

Delayed pull_request battery on already-merged PR #11426
(head ba3164812acdac28dfe217a9a16ab1e793a31bd8, merge-ref
a09a74ceec0017cbba47c9f02e4c7166d3836a5d) failed 141 files.
Later KEEP-lifts already matched living KEEP dicts of reminted
shared files. This leftover closes KEEP-lift tests that still
froze the previous hub/boards/autogtm live prefixes. Do not
remint leftover receipts. Historical SOURCE_REV maps stay on
their frozen trees.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HUB = "44bbd2ec"
STALE_HUB = "d0bd0e8d"
BOARDS = "e4b46040"
STALE_BOARDS = "143730a0"
AUTOGTM = "2fe108f4"
STALE_AUTOGTM = "dbbc96a5"
ORIGINALS = (
    "test_keep_sell_hub_pages_keep_lift.py",
    "test_grokbuild_harborline_hub_pages_keep_unpin.py",
    "test_harborline_pack_market_render_readback_rematch.py",
    "test_pr7915_closed_unmerged.py",
    "test_commerce_agents.py",
    "test_digit_clans_html_seat_note_20260909_01.py",
    "test_open_door_guard.py",
)
RECEIPT = ROOT / "p/grokbuild-tests-battery-34391842490-keep-lift-20260910-01.md"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTestsBattery34391842490KeepLift(unittest.TestCase):
    def test_live_hub_boards_autogtm_match_lifted_prefixes(self) -> None:
        hub = git_blob("hub_pages.py")
        boards = git_blob("boards.html")
        autogtm = git_blob("autogtm.html")
        self.assertTrue(hub.startswith(HUB), hub)
        self.assertFalse(hub.startswith(STALE_HUB), hub)
        self.assertTrue(boards.startswith(BOARDS), boards)
        self.assertFalse(boards.startswith(STALE_BOARDS), boards)
        self.assertTrue(autogtm.startswith(AUTOGTM), autogtm)
        self.assertFalse(autogtm.startswith(STALE_AUTOGTM), autogtm)

    def test_leftover_keep_lift_carriers_no_longer_freeze_stale_prefixes(self) -> None:
        keep_sell = (ROOT / "test_keep_sell_hub_pages_keep_lift.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(f'HUB_BLOB = "{HUB}"', keep_sell)
        self.assertIn(f'BOARDS_BLOB = "{BOARDS}"', keep_sell)
        self.assertNotIn(f'HUB_BLOB = "{STALE_HUB}"', keep_sell)
        self.assertNotIn(f'BOARDS_BLOB = "{STALE_BOARDS}"', keep_sell)
        unpin = (ROOT / "test_grokbuild_harborline_hub_pages_keep_unpin.py").read_text(
            encoding="utf-8"
        )
        rematch = (
            ROOT / "test_harborline_pack_market_render_readback_rematch.py"
        ).read_text(encoding="utf-8")
        pr7915 = (ROOT / "test_pr7915_closed_unmerged.py").read_text(encoding="utf-8")
        self.assertIn(f'startswith("{HUB}")', unpin)
        self.assertNotIn(f'startswith("{STALE_HUB}")', unpin)
        self.assertIn(f'startswith("{HUB}")', rematch)
        self.assertNotIn(f'startswith("{STALE_HUB}")', rematch)
        self.assertIn(f'startswith("{AUTOGTM}")', pr7915)
        self.assertNotIn(f'startswith("{STALE_AUTOGTM}")', pr7915)

    def test_keep_sell_row_stays_on_hub_and_boards(self) -> None:
        href = 'href="./keep-sell.html"'
        title = ">KEEP vs SELL</a>"
        copy = "Factory classification ledger. Marketing stays Bryce. No invented Stripe URLs."
        for rel in ("hub_pages.py", "boards.html"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(href, text)
            self.assertIn(title, text)
            self.assertIn(copy, text)
            self.assertEqual(text.count(href), 1)

    def test_originally_failing_keep_graph_contracts_pass(self) -> None:
        for name in ORIGINALS:
            with self.subTest(name=name):
                proc = subprocess.run(
                    ["python3", name],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    msg=f"{name}\n{proc.stdout}\n{proc.stderr}",
                )

    def test_did_not_remint_leftover_receipts(self) -> None:
        leftover = ROOT / "p/cursor-claude-commerce-agents-20260902-01.md"
        self.assertTrue(leftover.is_file())
        blob = git_blob("p/cursor-claude-commerce-agents-20260902-01.md")
        self.assertTrue(blob.startswith("3e48f691"), leftover)
        self.assertTrue(
            git_blob("p/cursor-harborline-pack-market-render-20260902-01.md").startswith(
                "54c348dc"
            )
        )
        digit = ROOT / "p/digit-clans-html-seat-note-20260909-01.md"
        self.assertTrue(digit.is_file())
        self.assertIn("DIGIT", digit.read_text(encoding="utf-8"))
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("34391842490", receipt)
        self.assertIn(
            "woahwhattheheck/commons:tests:ba3164812acdac28dfe217a9a16ab1e793a31bd8:the whole battery, one failure fails the run",
            receipt,
        )
        self.assertNotIn('type="password"', (ROOT / "hub_pages.py").read_text(encoding="utf-8"))
        self.assertNotIn("Authorization", (ROOT / "hub_pages.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
