#!/usr/bin/env python3
"""Pin grok-build leftover for run 33682674896 occupancy KEEP already on main."""

from __future__ import annotations

import importlib
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-stealable-occupancy-keep-match-20260902-01.md"
LIFT = ROOT / "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md"
OCCUPANCY = ROOT / "p/cursor-stealable-lanes-occupancy-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-stealable-lanes-roles-20260902-01.md"
HELPER = ROOT / "host/stealable_lanes.py"

KEEP_UNREAD = {
    "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md": "67a8a527",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-stealable-lanes-roles-readback-20260902-01.md": "ada92980",
    "p/grokbuild-pr8353-stealable-lanes-20260902-01.md": "87bdb237",
    "p/grok-build-pr8353-caec56f3-terminal-20260902-01.md": "7e8db90d",
    "ground/OWNER_NOW.md": "59b1fd37",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
    "autogtm.html": "9d8b3e85",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildStealableOccupancyKeepMatch(unittest.TestCase):
    def test_occupancy_keep_no_longer_freezes_stale_stealable_test(self) -> None:
        occ = importlib.import_module("test_stealable_lanes_occupancy")
        self.assertNotEqual(occ.KEEP.get("test_stealable_lanes.py"), "721adc44")
        self.assertTrue(git_blob("test_stealable_lanes.py").startswith("a4d48d19"))
        occupancy = subprocess.run(
            ["python3", "-m", "unittest", "test_stealable_lanes_occupancy.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(occupancy.returncode, 0, msg=occupancy.stdout + occupancy.stderr)
        self.assertIn("Ran 4 tests", occupancy.stderr)
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_stealable_lanes.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 4 tests", leftover.stderr)

    def test_keep_unread_peer_leftovers_and_helper_refuses_send(self) -> None:
        for rel, prefix in KEEP_UNREAD.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        check = subprocess.run(
            ["python3", str(HELPER), "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(check.returncode, 0, msg=check.stdout + check.stderr)
        self.assertIn("ok", check.stdout)
        payload = json.loads(
            subprocess.run(
                ["python3", str(HELPER), "--json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            ).stdout
        )
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(payload["cash_usd"], 0)
        self.assertEqual(payload["sends"], 0)
        for flag in ("--send", "--go"):
            refused = subprocess.run(
                ["python3", str(HELPER), flag],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(refused.returncode, 2, msg=refused.stdout + refused.stderr)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())

    def test_unique_receipt_already_merged_verified(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        lift = LIFT.read_text(encoding="utf-8")
        occupancy = OCCUPANCY.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("id: grokbuild-stealable-occupancy-keep-match-20260902-01", text)
        self.assertIn("33682674896", text)
        self.assertIn("61af2da31c60f2ad93b484888ecff202bdcfb52c", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8353", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8397", text)
        self.assertIn("03f81047", text)
        self.assertIn("721adc44", text)
        self.assertIn("a4d48d19", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("67a8a527", text)
        self.assertIn("5f1ef25f", text)
        self.assertIn("c90284fb", text)
        self.assertIn("9631e869", text)
        self.assertIn("NOT_MINTED", text)
        self.assertIn("Did not remint leftover", text)
        self.assertNotEqual(text, lift)
        self.assertNotEqual(text, occupancy)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("No auth", text)


if __name__ == "__main__":
    unittest.main()
