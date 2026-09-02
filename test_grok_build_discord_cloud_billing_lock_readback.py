#!/usr/bin/env python3
"""Pin unique-pack readback of Discord billing-lock leftover. Do not fake green."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-discord-cloud-billing-lock-readback-20260902-01.md"
LEFTOVER = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"

KEEP = {
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "commons_discord.py": "f6f1a374",
    "discord_ingest.py": "51a73262",
    "test_commons_discord.py": "5881bb78",
    "test_discord_mirror.py": "45043494",
    "infra/discord/test_commons_discord_bridge.py": "9c623e59",
    "infra/discord/test_windows_runtime.py": "158feb48",
    ".github/workflows/commons-discord-cloud.yml": "6f1c1479",
    "p/grok-discord-cloud-dark-20260831-01.md": "cdbad10b",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "host/merge_on_pr.py": "0270094d",
    "p/cursor-mcp-get-grounding-readback-20260902-01.md": "4d7bc317",
    "p/cursor-stealable-lanes-occupancy-readback-20260902-01.md": "b2df1cf1",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokBuildDiscordCloudBillingLockReadback(unittest.TestCase):
    def test_keep_leftover_helpers_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_receipt_stays_external_blocker(self) -> None:
        text = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("state: EXTERNAL_BLOCKER", text)
        self.assertIn("33686687878", text)
        self.assertIn("No fake green", text)
        self.assertIn("Did not remint grok-discord-cloud-dark-20260831-01", text)
        self.assertNotIn("buy.stripe.com", text)

    def test_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_commons_discord.py",
                "test_discord_mirror.py",
                "infra/discord/test_commons_discord_bridge.py",
                "infra/discord/test_windows_runtime.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 34 tests", proc.stderr)

    def test_adjacent_item6_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_merge_on_pr.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 6 tests", proc.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("grok-build-discord-cloud-billing-lock-readback-20260902-01", text)
        self.assertIn("18c4b3df5", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("Did **not** remint", text)
        self.assertIn("Did **not** fake green", text)
        self.assertIn("Did **not** unique-pack this seat item 6", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
