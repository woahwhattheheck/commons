#!/usr/bin/env python3
"""Pin unique leftover for main-range-verify run 33717084528. Do not remint range contract or prior leftovers."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grok-build-job-watchdog-33699286811-billing-lock-20260903-01.md"
KEEP_POST = ROOT / "p/grokbuild-pr8546-verify-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/main-range-verify.yml"

KEEP = {
    ".github/workflows/main-range-verify.yml": "029f912a",
    "host/main_range.py": "6acdc3d9",
    "host/main_velocity.py": "b34a1241",
    "test_main_range.py": "2cfa7313",
    "open_door_guard.py": "4b053e43",
    "p/codex-main-range-open-door-repair-20260830-01.md": "bfba0568",
    "p/grokbuild-pr8546-verify-20260903-01.md": "4e4d8003",
    "p/grok-build-job-watchdog-33699286811-billing-lock-20260903-01.md": "81092ec2",
    "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md": "43c6e5cb",
    "p/grokbuild-open-door-guard-33699940644-billing-lock-20260903-01.md": "38fc515e",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildMainRangeVerify33717084528BillingLock(unittest.TestCase):
    def test_keep_range_contract_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 host/main_range.py", yml)
        self.assertIn("--head HEAD", yml)
        self.assertIn("--lookback-minutes", yml)
        self.assertIn("group: commons-main-range-verify", yml)
        self.assertIn("cancel-in-progress: false", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        keep_post = KEEP_POST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-main-range-verify-33717084528-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:main-range-verify:f13f3552dc3d8ad812cc6f26e48e97eb8cad9791:verify-range",
            text,
        )
        self.assertIn("33717084528", text)
        self.assertIn("100528437809", text)
        self.assertIn("100529274610", text)
        self.assertIn("f13f3552dc3d8ad812cc6f26e48e97eb8cad9791", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grokbuild-pr8546-verify-20260903-01", text)
        self.assertIn("4e4d8003", text)
        self.assertIn("81092ec2", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("38fc515e", text)
        self.assertIn("d22e0707", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("bfba0568", text)
        self.assertIn("029f912a", text)
        self.assertIn("6acdc3d9", text)
        self.assertIn("b34a1241", text)
        self.assertIn("2cfa7313", text)
        self.assertIn("4b053e43", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, keep_post)
        self.assertNotIn(
            "main-range-verify:f13f3552dc3d8ad812cc6f26e48e97eb8cad9791:verify-range",
            prior,
        )
        self.assertNotIn(
            "main-range-verify:f13f3552dc3d8ad812cc6f26e48e97eb8cad9791:verify-range",
            keep_post,
        )

    def test_local_range_still_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "main-range.json"
            proc = subprocess.run(
                [
                    "python3",
                    "host/main_range.py",
                    "--head",
                    "HEAD",
                    "--lookback-minutes",
                    "30",
                    "--receipt",
                    str(receipt),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            payload = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(payload.get("status"), "PASS")
        self.assertEqual(payload.get("observations", {}).get("finding_count"), 0)
        self.assertEqual(
            [row["exit_code"] for row in payload.get("results", [])],
            [0] * len(payload.get("results", [])),
        )

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "main-range-verify.yml job verify-range executes "
                "python3 host/main_range.py --head HEAD --lookback-minutes 30 "
                "and uploads the receipt artifact"
            ),
            "repair_attempts": [
                "local test_main_range.py 10/10",
                "local host/main_range.py lookback 30 status PASS rc=0",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal",
                "GitHub Actions billing APIs 404",
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
