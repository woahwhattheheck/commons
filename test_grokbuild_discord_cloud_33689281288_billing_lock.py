#!/usr/bin/env python3
"""Pin unique leftover for commons-discord-cloud run 33689281288. Do not remint prior leftover or relay."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-discord-cloud-33689281288-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"
READBACK = ROOT / "p/grok-build-discord-cloud-billing-lock-readback-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/commons-discord-cloud.yml"

KEEP = {
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-discord-cloud-billing-lock-readback-20260902-01.md": "e14e443b",
    "test_grok_build_discord_cloud_billing_lock_readback.py": "8622a8ce",
    ".github/workflows/commons-discord-cloud.yml": "6f1c1479",
    "commons_discord.py": "f6f1a374",
    "discord_ingest.py": "51a73262",
    "test_commons_discord.py": "5881bb78",
    "test_discord_mirror.py": "45043494",
    "infra/discord/test_commons_discord_bridge.py": "9c623e59",
    "infra/discord/test_windows_runtime.py": "158feb48",
    "infra/discord/assert_ready.py": "ad33fdba",
    "p/grok-discord-cloud-dark-20260831-01.md": "cdbad10b",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildDiscordCloud33689281288BillingLock(unittest.TestCase):
    def test_keep_relay_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 commons_discord.py to-discord send", yml)
        self.assertIn("assert_ready.py commons_to_discord", yml)
        self.assertIn("python3 commons_discord.py sync-in", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertIn("runs-on: ubuntu-latest", yml)

    def test_local_failed_step_still_passes(self) -> None:
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
        out = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, msg=out)
        self.assertIn("Ran 34 tests", out)
        self.assertIn("OK", out)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        readback = READBACK.read_text(encoding="utf-8")
        self.assertIn("grok-build-discord-cloud-33689281288-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:commons-discord-cloud:81e8f9ccc7293bf6e5179e615ba460d87f409eb0:outbound",
            text,
        )
        self.assertIn("33689281288", text)
        self.assertIn("100444021565", text)
        self.assertIn("81e8f9ccc7293bf6e5179e615ba460d87f409eb0", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8415", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-discord-cloud-billing-lock-20260902-01", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("e14e443b", text)
        self.assertIn("6f1c1479", text)
        self.assertIn("f6f1a374", text)
        self.assertIn("did not reopen #7915", text)
        self.assertIn("Did not reopen #8400", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, readback)
        self.assertNotIn(
            "commons-discord-cloud:81e8f9ccc7293bf6e5179e615ba460d87f409eb0:outbound",
            prior,
        )
        self.assertIn(
            "commons-discord-cloud:8b42a78e0fa73ba3d343d8e8e78d6ca5d1a7be03:outbound",
            prior,
        )
        self.assertNotIn("buy.stripe.com", text)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "commons-discord-cloud.yml job outbound executes "
                "python3 commons_discord.py doctor, "
                "infra/discord/assert_ready.py commons_to_discord, "
                "then to-discord send of newly landed p/*.md on push to main"
            ),
            "repair_attempts": [
                "inspected commons-discord-cloud.yml — valid outbound, no skip",
                "local discord battery 34/34 OK",
                "test_merge_on_pr.py 6/6 OK",
                "to-discord format rc=0",
                "later sibling runs 733-735 same billing lock",
                "GitHub connector get_job_logs 404; billing API 404",
            ],
            "blocker": (
                "GitHub Actions ubuntu-latest never assigned: "
                "The job was not started because your account is locked due to a billing issue."
            ),
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        }
        self.assertEqual(fix_first.validate(packet)["state"], "EXTERNAL_BLOCKER")


if __name__ == "__main__":
    unittest.main()
