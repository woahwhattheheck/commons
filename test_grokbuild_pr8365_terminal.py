#!/usr/bin/env python3
"""Pin grok-build terminal leftover for PR 8365. Do not remint landed-work feed leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/landed_work_feed.py"
READBACK = ROOT / "p/cursor-landed-work-feed-readback-20260902-01.md"
READBACK_TEST = ROOT / "test_landed_work_feed_readback.py"
LEFTOVER = ROOT / "p/cursor-landed-work-feed-20260902-01.md"
RECEIPT = ROOT / "p/grokbuild-pr8365-terminal-20260902-01.md"

KEEP = {
    "p/cursor-landed-work-feed-readback-20260902-01.md": "d37eb307",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "host/landed_work_feed.py": "0506fd0f",
    "ground/LANDED_WORK_FEED.json": "4c42f69f",
    "landed-work.html": "93cfe179",
    "repo_pulse.py": "5d716a63",
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


class TestGrokbuildPr8365Terminal(unittest.TestCase):
    def test_keep_unique_pack_and_leftover_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_tests_keep_lifted_after_337_remint(self) -> None:
        self.assertNotEqual(KEEP.get("test_landed_work_feed.py"), "1c35b970")
        self.assertNotEqual(KEEP.get("test_landed_work_feed_readback.py"), "cb58ab08")
        self.assertTrue(git_blob("test_landed_work_feed.py").startswith("3f7919e0"))
        self.assertTrue(
            git_blob("test_landed_work_feed_readback.py").startswith("932ba427")
        )
        self.assertTrue(
            git_blob("p/grokbuild-pr8365-terminal-20260902-01.md").startswith("212208a2")
        )
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_landed_work_feed.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        readback = subprocess.run(
            ["python3", "-m", "unittest", "test_landed_work_feed_readback.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(readback.returncode, 0, msg=readback.stdout + readback.stderr)

    def test_leftover_helper_still_per_merge_and_refuses_send(self) -> None:
        proc = run_helper("--json", "--limit", "3")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertEqual(packet["cadence"], "per-merge")
        self.assertTrue(packet["not_per_day"])
        self.assertEqual(packet["sends"], 0)
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["unnamed_remainder"], "FINDER-FAILED")
        for flag in ("--send", "--apply", "--go", "--autopilot"):
            refused = run_helper(flag)
            self.assertEqual(refused.returncode, 2, msg=refused.stdout + refused.stderr)
            payload = json.loads(refused.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)

    def test_receipt_cites_8365_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        readback = READBACK.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8365-terminal-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8365@25586897b9a8fa155bf9b371f59d89da59a45ba7",
            text,
        )
        self.assertIn("e5b7f5ac2bbaafa6524ab9ea971ea300f9e99b76", text)
        self.assertIn("d37eb3077467c4566b1f68199e5993958eaa0eb6", text)
        self.assertIn("cb58ab08ace7ddef787204eca21129e73a73cba1", text)
        self.assertIn("issuecomment-5516421346", text)
        self.assertIn("5/5 OK", text)
        self.assertIn("9/9 OK", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertNotEqual(text, readback)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertTrue(READBACK_TEST.is_file())


if __name__ == "__main__":
    unittest.main()
