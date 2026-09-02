#!/usr/bin/env python3
"""Pin unique-pack readback of PR8399 #commons Slack leftover. Do not remint occupancy."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8399-commons-slack-readback-20260902-01.md"
LEFTOVER = ROOT / "p/grokbuild-pr8399-commons-slack-20260902-01.md"

KEEP = {
    "p/grokbuild-pr8399-commons-slack-20260902-01.md": "1905dd74",
    "p/grokbuild-stealable-occupancy-keep-match-20260902-01.md": "dc058b13",
    "test_grokbuild_stealable_occupancy_keep_match.py": "0705ff4d",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "p/cursor-stealable-lanes-roles-readback-20260902-01.md": "ada92980",
    "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md": "67a8a527",
    "p/cursor-stealable-lanes-occupancy-readback-20260902-01.md": "b2df1cf1",
    "p/grok-build-discord-cloud-billing-lock-readback-20260902-01.md": "e14e443b",
    "p/cursor-mcp-get-grounding-readback-20260902-01.md": "4d7bc317",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grokbuild-pr8402-verify-20260902-01.md": "3524e382",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
    "ground/OWNER_NOW.md": "59b1fd37",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8399CommonsSlackReadback(unittest.TestCase):
    def test_keep_leftover_occupancy_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_unique_tests_still_pass(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_grokbuild_stealable_occupancy_keep_match.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 3 tests", proc.stderr)

    def test_occupancy_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_stealable_lanes_occupancy.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr)

    def test_leftover_send_go_unrecognized(self) -> None:
        for flag in ("--send", "--go"):
            proc = subprocess.run(
                ["python3", "host/stealable_lanes.py", flag],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            combined = (proc.stdout + proc.stderr).lower()
            self.assertIn("unrecognized arguments", combined)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8399-commons-slack-readback-20260902-01", text)
        self.assertIn("3e519b2f2", text)
        self.assertIn("1905dd74", text)
        self.assertIn("Did **not** remint", text)
        self.assertIn("Did **not** unique-pack this seat item 6", text)
        self.assertIn("Did **not** unique-pack later billing-lock leftovers", text)
        self.assertIn("c1e63e76", leftover)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
