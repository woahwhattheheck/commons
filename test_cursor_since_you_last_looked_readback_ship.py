#!/usr/bin/env python3
"""SHIP leftover unique-pack since-you-last-looked readback. Do not remint leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/since_you_last_looked_readback_ship.py"
RECEIPT = ROOT / "p/cursor-since-you-last-looked-readback-ship-20260902-01.md"
UNIQUE = ROOT / "p/cursor-since-you-last-looked-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-since-you-last-looked-20260902-01.md"

KEEP = {
    "p/cursor-since-you-last-looked-20260902-01.md": "003828c9",
    "host/since_you_last_looked.py": "3578783c",
    "ground/SINCE_YOU_LAST_LOOKED.json": "749c8220",
    "test_since_you_last_looked.py": "7a7cbdec",
    "since-you-last-looked.html": "286328ed",
    "p/cursor-since-you-last-looked-readback-20260902-01.md": "bc71c9fe",
    "test_cursor_since_you_last_looked_readback.py": "43c868f7",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "p/cursor-stealable-lanes-roles-readback-20260902-01.md": "ada92980",
    "p/cursor-commons-slack-full-body-20260902-01.md": "86f4eddc",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "ground/OWNER_NOW.md": "59b1fd37",
    "grounding.html": "abb91caf",
    "hub_pages.py": "5ac12648",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def run_helper(*flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(HELPER), *flags],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class TestCursorSinceYouLastLookedReadbackShip(unittest.TestCase):
    def test_keep_leftover_and_unique_pack_exact(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_ship_receipt_cites_unique_pack_without_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        unique = UNIQUE.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-since-you-last-looked-readback-ship-20260902-01", text)
        self.assertIn("cursor-since-you-last-looked-readback-20260902-01", text)
        self.assertIn("cursor-since-you-last-looked-20260902-01", text)
        self.assertIn("a2dec477a", text)
        self.assertIn("15986f8a0", text)
        self.assertIn("bc71c9fe", text)
        self.assertIn("3285", text)
        self.assertIn("186a3e4a", text)
        self.assertIn("003828c9", text)
        self.assertIn("#8393", text)
        self.assertIn("6/6", text)
        self.assertIn("bc-92648f95", text)
        self.assertIn("bc-73365238", text)
        self.assertIn("bc-31c8ef9a", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not take item 11", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("Sends 0", text)
        self.assertNotEqual(text, unique)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())

    def test_send_apply_go_refused(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["item_11"])

    def test_unknown_args_finder_failed_not_zero(self) -> None:
        proc = run_helper("--not-a-real-flag")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")

    def test_ship_classifies_unique_pack_on_current_main(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ship_ok"])
        self.assertEqual(payload["verdict"], "SHIP")
        self.assertEqual(
            payload["unique_pack_id"],
            "cursor-since-you-last-looked-readback-20260902-01",
        )
        self.assertEqual(
            payload["leftover_id"],
            "cursor-since-you-last-looked-20260902-01",
        )
        self.assertEqual(payload["unique_land"], "a2dec477a")
        self.assertEqual(payload["leftover_land"], "15986f8a0")
        self.assertEqual(payload["pr"], 8393)
        self.assertEqual(payload["receipt_blob"], "bc71c9fe")
        self.assertEqual(payload["receipt_bytes"], 3285)
        self.assertEqual(payload["receipt_sha256"], "186a3e4a")
        self.assertEqual(payload["leftover_blob"], "003828c9")
        self.assertEqual(payload["leftover_tests"], "6/6")
        self.assertEqual(payload["send_rc"], 2)
        self.assertEqual(payload["go_rc"], 2)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["cash"], 0)
        self.assertEqual(payload["checkout"], "FINDER-FAILED")
        self.assertEqual(payload["grouped_by"], ["git", "slack", "commons"])
        self.assertTrue(payload["nothing_dropped"])
        self.assertFalse(payload["model_decides_what_matters"])
        self.assertTrue(payload["not_per_merge_line"])
        self.assertEqual(payload["bryce_pinned"], 1)
        self.assertEqual(payload["bryce_pin_ts"], "1788380844.707619")
        self.assertEqual(payload["slack_live_token"], "FINDER-FAILED")
        self.assertFalse(payload["item_11"])
        self.assertFalse(payload["login"])
        self.assertFalse(payload["gate"])
        self.assertTrue(payload["did_not_remint_leftover"])
        self.assertTrue(payload["did_not_remint_unique_pack"])
        self.assertTrue(payload["did_not_take_item_11"])
        self.assertEqual(
            payload["keep_blobs"]["p/cursor-since-you-last-looked-20260902-01.md"],
            "003828c9",
        )
        self.assertEqual(
            payload["keep_blobs"]["p/cursor-since-you-last-looked-readback-20260902-01.md"],
            "bc71c9fe",
        )


if __name__ == "__main__":
    unittest.main()
