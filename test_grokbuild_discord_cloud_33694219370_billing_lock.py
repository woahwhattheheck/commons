#!/usr/bin/env python3
"""Pin unique leftover for commons-discord-cloud run 33694219370. Do not remint prior leftovers or Discord helpers."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-discord-cloud-33694219370-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"
READBACK = ROOT / "p/grok-build-discord-cloud-billing-lock-readback-20260902-01.md"
PRIOR_RUN = ROOT / "p/grok-build-discord-cloud-33689083145-billing-lock-20260902-01.md"
PRIOR_RUN2 = ROOT / "p/grok-build-discord-cloud-33689281288-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/commons-discord-cloud.yml"

KEEP = {
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-discord-cloud-billing-lock-readback-20260902-01.md": "e14e443b",
    "test_grok_build_discord_cloud_billing_lock_readback.py": "8622a8ce",
    "p/grok-build-discord-cloud-33689083145-billing-lock-20260902-01.md": "6e34f897",
    "p/grok-build-discord-cloud-33689281288-billing-lock-20260902-01.md": "89fdbcf0",
    "p/grok-discord-cloud-dark-20260831-01.md": "cdbad10b",
    "p/wire-hub-tick-20260902-01.md": "33e99713",
    "commons_discord.py": "f6f1a374",
    "discord_ingest.py": "51a73262",
    "test_commons_discord.py": "5881bb78",
    "test_discord_mirror.py": "45043494",
    "infra/discord/test_commons_discord_bridge.py": "9c623e59",
    "infra/discord/test_windows_runtime.py": "158feb48",
    "infra/discord/assert_ready.py": "ad33fdba",
    ".github/workflows/commons-discord-cloud.yml": "6f1c1479",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildDiscordCloud33694219370BillingLock(unittest.TestCase):
    def test_keep_helpers_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 infra/discord/assert_ready.py commons_to_discord", yml)
        self.assertIn("python3 commons_discord.py to-discord send", yml)
        self.assertIn("python3 commons_discord.py sync-in", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("continue-on-error: true", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertIn("runs-on: ubuntu-latest", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        readback = READBACK.read_text(encoding="utf-8")
        prior_run = PRIOR_RUN.read_text(encoding="utf-8")
        prior_run2 = PRIOR_RUN2.read_text(encoding="utf-8")
        self.assertIn("grok-build-discord-cloud-33694219370-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:commons-discord-cloud:6b2a01e8ff3a23b021448f8cb9a80709ff300d26:outbound",
            text,
        )
        self.assertIn("33694219370", text)
        self.assertIn("100459480542", text)
        self.assertIn("100461212551", text)
        self.assertIn("6b2a01e8ff3a23b021448f8cb9a80709ff300d26", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("state: EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-discord-cloud-billing-lock-20260902-01", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("e14e443b", text)
        self.assertIn("6e34f897", text)
        self.assertIn("89fdbcf0", text)
        self.assertIn("cdbad10b", text)
        self.assertIn("f6f1a374", text)
        self.assertIn("6f1c1479", text)
        self.assertIn("33e99713", text)
        self.assertIn("did not reopen #7915", text)
        self.assertIn("did not reopen #8400", text)
        self.assertIn("No fake green", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, readback)
        self.assertNotEqual(text, prior_run)
        self.assertNotEqual(text, prior_run2)
        self.assertNotIn("33694219370", prior)
        self.assertNotIn(
            "commons-discord-cloud:6b2a01e8ff3a23b021448f8cb9a80709ff300d26:outbound",
            prior,
        )
        self.assertNotIn("buy.stripe.com", text)

    def test_discord_battery_and_format_still_pass(self) -> None:
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
        fmt = subprocess.run(
            [
                "python3",
                "commons_discord.py",
                "to-discord",
                "format",
                "p/wire-hub-tick-20260902-01.md",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(fmt.returncode, 0, msg=fmt.stdout + fmt.stderr)
        self.assertIn("source_id: wire-hub-tick-20260902-01", fmt.stdout)

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

    def test_open_door_guard_and_fix_first_external_blocker(self) -> None:
        added = [
            guard.AddedLine(str(RECEIPT.relative_to(ROOT)), i + 1, line)
            for i, line in enumerate(RECEIPT.read_text(encoding="utf-8").splitlines())
        ]
        added.extend(
            guard.AddedLine(str(Path(__file__).relative_to(ROOT)), i + 1, line)
            for i, line in enumerate(Path(__file__).read_text(encoding="utf-8").splitlines())
        )
        self.assertEqual(guard.scan_added(added), [])
        packet = {
            "outcome": "external_blocker",
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
            "observed_broken": True,
            "finding_kind": "behavior",
            "prior_door_state": "not_applicable",
            "expected_contract": "commons-discord-cloud outbound starts an ubuntu-latest runner and mirrors newly landed p/*.md",
            "repair_attempts": [
                "inspected commons-discord-cloud.yml blob 6f1c1479",
                "local discord battery 34/34",
                "test_merge_on_pr.py 6/6",
                "to-discord format p/wire-hub-tick-20260902-01.md rc=0",
                "github rerun_failed_jobs 201",
                "attempt 2 job 100461212551 same billing lock",
            ],
            "blocker": "The job was not started because your account is locked due to a billing issue.",
        }
        result = fix_first.validate(packet)
        self.assertEqual(result["state"], "EXTERNAL_BLOCKER")
        proc = subprocess.run(
            ["python3", "fix_first.py", "--json", json.dumps(packet)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("EXTERNAL_BLOCKER", proc.stdout)


if __name__ == "__main__":
    unittest.main()
