#!/usr/bin/env python3
"""Pin unique PR 8635 already-merged verify. Do not remint original leftovers."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8635-already-merged-verify-20260903-01.md"
ORIGINAL = ROOT / "p/grok-build-commons-board-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/commons-board.yml"
BODY_SHA256 = "4e64d46e75b9dab032e758e52e19a4156fd9da00b5dcd18c3d126f315faf0250"

KEEP = {
    "p/grok-build-commons-board-billing-lock-20260903-01.md": "c07bf913",
    ".github/workflows/commons-board.yml": "ce1c2867",
    "board_ingest.py": "7c6c5b8c",
    "open_door_guard.py": "4b053e43",
    "enqueue_pending_grok_com.py": "d1e4b9e7",
    "fix_first.py": "a57aee1c",
    "p/grok-build-repo-pulse-billing-lock-20260903-01.md": "b6e5953c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8635AlreadyMergedVerify(unittest.TestCase):
    def test_original_leftovers_and_publisher_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 board_ingest.py --publish", yml)
        self.assertIn("runs-on: ubuntu-24.04-arm", yml)
        self.assertIn("ref: main", yml)
        self.assertIn("cancel-in-progress: false", yml)
        self.assertNotIn("if: false", yml)

    def test_verify_receipt_is_unique(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        original = ORIGINAL.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8635-already-merged-verify-20260903-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8635", text)
        self.assertIn("33722889836", text)
        self.assertIn("100547146353", text)
        self.assertIn(
            "woahwhattheheck/commons:commons-board:35ac733fbcf265852bc04e6400ef308a5b82104b:ingest",
            text,
        )
        self.assertIn("35ac733fbcf265852bc04e6400ef308a5b82104b", text)
        self.assertIn("37324dd392930e10bca0284f2bfd5f905b02bb83", text)
        self.assertIn("f0a980053dae781f35e8723428d42aae64b7a5d3", text)
        self.assertIn("c07bf913", text)
        self.assertIn("ce1c2867", text)
        self.assertIn("7c6c5b8c", text)
        self.assertIn("4b053e43", text)
        self.assertIn("b6e5953c", text)
        self.assertIn("741654e695d814c09f5182a98146404cb4edc98d874d298a47196918efe4dca7", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-commons-board-billing-lock-20260903-01", text)
        self.assertIn("issuecomment-5521595483", text)
        self.assertIn("issuecomment-5521599437", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8635-already-merged-verify-20260903-01", original)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)

    def test_publisher_checkout_contract_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "test_board_checkout_head.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("BOARD CHECKOUT HEAD TEST", proc.stdout)
        fanout = subprocess.run(
            ["python3", "-m", "unittest", "test_board_issue_fanout.py", "test_enqueue_pending_grok_com.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(fanout.returncode, 0, msg=fanout.stdout + fanout.stderr)
        self.assertIn("Ran 14 tests", fanout.stderr + fanout.stdout)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "commons-board.yml job ingest assigns ubuntu-24.04-arm, "
                "checks out ref main, and runs python3 board_ingest.py --publish"
            ),
            "repair_attempts": [
                "local test_board_checkout_head.py PASS",
                "local test_board_issue_fanout.py 7/7",
                "local test_enqueue_pending_grok_com.py 7/7",
                "local test_device_action_state.py 22/22",
                "github rerun_failed_jobs attempt 2 same billing refusal",
                "GitHub Actions billing APIs unavailable; no Actions-billing write road",
            ],
            "blocker": (
                "GitHub Actions ubuntu-24.04-arm never assigned: "
                "The job was not started because your account is locked due to a billing issue."
            ),
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        }
        self.assertEqual(fix_first.validate(packet)["state"], "EXTERNAL_BLOCKER")
        proc = subprocess.run(
            ["python3", "fix_first.py", "--json", __import__("json").dumps(packet)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("EXTERNAL_BLOCKER", proc.stdout)


if __name__ == "__main__":
    unittest.main()
