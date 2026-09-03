#!/usr/bin/env python3
"""Pin unique leftover for commons-discord-cloud run 33699986516. Do not remint prior leftovers or Discord helpers."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-discord-cloud-33699986516-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"
READBACK = ROOT / "p/grok-build-discord-cloud-billing-lock-readback-20260902-01.md"
PRIOR_RUN = ROOT / "p/grok-build-discord-cloud-33689083145-billing-lock-20260902-01.md"
PRIOR_RUN2 = ROOT / "p/grok-build-discord-cloud-33689281288-billing-lock-20260902-01.md"
PRIOR_RUN3 = ROOT / "p/grok-build-discord-cloud-33694219370-billing-lock-20260902-01.md"
PRIOR_RUN4 = ROOT / "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md"
PRIOR_RUN5 = ROOT / "p/grok-build-discord-cloud-33699607389-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/commons-discord-cloud.yml"

KEEP = {
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-discord-cloud-billing-lock-readback-20260902-01.md": "e14e443b",
    "test_grok_build_discord_cloud_billing_lock_readback.py": "8622a8ce",
    "p/grok-build-discord-cloud-33689083145-billing-lock-20260902-01.md": "6e34f897",
    "p/grok-build-discord-cloud-33689281288-billing-lock-20260902-01.md": "89fdbcf0",
    "p/grok-build-discord-cloud-33694219370-billing-lock-20260902-01.md": "9dcc171b",
    "test_grokbuild_discord_cloud_33694219370_billing_lock.py": "b09b44aa",
    "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md": "e8d308ed",
    "test_grokbuild_discord_cloud_33699286743_billing_lock.py": "fcc155e0",
    "p/grok-build-discord-cloud-33699607389-billing-lock-20260903-01.md": "0a4e42d4",
    "test_grokbuild_discord_cloud_33699607389_billing_lock.py": "4a0c3a98",
    "p/grok-discord-cloud-dark-20260831-01.md": "cdbad10b",
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


class TestGrokbuildDiscordCloud33699986516BillingLock(unittest.TestCase):
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
        prior_run3 = PRIOR_RUN3.read_text(encoding="utf-8")
        prior_run4 = PRIOR_RUN4.read_text(encoding="utf-8")
        prior_run5 = PRIOR_RUN5.read_text(encoding="utf-8")
        self.assertIn("grok-build-discord-cloud-33699986516-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:commons-discord-cloud:dd428e4e3d774588fe5f5d2801b2acf7c9db67b7:outbound",
            text,
        )
        self.assertIn("33699986516", text)
        self.assertIn("100477000836", text)
        self.assertIn("100478545758", text)
        self.assertIn("dd428e4e3d774588fe5f5d2801b2acf7c9db67b7", text)
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
        self.assertIn("9dcc171b", text)
        self.assertIn("e8d308ed", text)
        self.assertIn("fcc155e0", text)
        self.assertIn("0a4e42d4", text)
        self.assertIn("4a0c3a98", text)
        self.assertIn("cdbad10b", text)
        self.assertIn("f6f1a374", text)
        self.assertIn("6f1c1479", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8400", text)
        self.assertIn("No fake green", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, readback)
        self.assertNotEqual(text, prior_run)
        self.assertNotEqual(text, prior_run2)
        self.assertNotEqual(text, prior_run3)
        self.assertNotEqual(text, prior_run4)
        self.assertNotEqual(text, prior_run5)
        self.assertNotIn("33699986516", prior)
        self.assertNotIn("33699986516", prior_run4)
        self.assertNotIn("33699986516", prior_run5)
        self.assertNotIn(
            "commons-discord-cloud:dd428e4e3d774588fe5f5d2801b2acf7c9db67b7:outbound",
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
                "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(fmt.returncode, 0, msg=fmt.stdout + fmt.stderr)
        self.assertIn(
            "source_id: grok-build-discord-cloud-33699286743-billing-lock-20260902-01",
            fmt.stdout,
        )

    def test_adjacent_item6_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_merge_on_pr.py", "test_path_manifest.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 15 tests", proc.stderr)

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
                "test_path_manifest.py 9/9",
                "to-discord format p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md rc=0",
                "github rerun_failed_jobs 201",
                "attempt 2 job 100478545758 same billing lock",
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
