#!/usr/bin/env python3
"""Pin unique leftover for harness-wakeup run 33717474657. Do not remint bake contract or prior leftovers."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import fix_first
import wakeup

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md"
KEEP_POST = ROOT / "p/grokbuild-pr8546-verify-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/harness-wakeup.yml"

KEEP = {
    ".github/workflows/harness-wakeup.yml": "813043ab",
    "wakeup.py": "7988ceb2",
    "test_wakeup_reliability.py": "aca39ab4",
    "open_door_guard.py": "4b053e43",
    "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md": "2b0fd9c9",
    "test_grokbuild_main_range_verify_33717084528_billing_lock.py": "3e89a404",
    "p/grokbuild-pr8546-verify-20260903-01.md": "4e4d8003",
    "p/grok-build-job-watchdog-33699286811-billing-lock-20260903-01.md": "81092ec2",
    "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md": "43c6e5cb",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildHarnessWakeup33717474657BillingLock(unittest.TestCase):
    def test_keep_bake_contract_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 wakeup.py", yml)
        self.assertIn("git add wakeups.json wakeups/fired.json", yml)
        self.assertIn("git push origin HEAD:main", yml)
        self.assertIn("cron: \"2,17,32,47 * * * *\"", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        keep_post = KEEP_POST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:harness-wakeup:f13f3552dc3d8ad812cc6f26e48e97eb8cad9791:bake",
            text,
        )
        self.assertIn("33717474657", text)
        self.assertIn("100529592819", text)
        self.assertIn("100530825224", text)
        self.assertIn("f13f3552dc3d8ad812cc6f26e48e97eb8cad9791", text)
        self.assertIn("0ddbdaf51fee6870caf1572ff53db1293852b72b", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grokbuild-main-range-verify-33717084528-billing-lock-20260903-01", text)
        self.assertIn("2b0fd9c9", text)
        self.assertIn("3e89a404", text)
        self.assertIn("4e4d8003", text)
        self.assertIn("81092ec2", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("813043ab", text)
        self.assertIn("7988ceb2", text)
        self.assertIn("aca39ab4", text)
        self.assertIn("4b053e43", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, keep_post)
        self.assertNotIn(
            "harness-wakeup:f13f3552dc3d8ad812cc6f26e48e97eb8cad9791:bake",
            prior,
        )
        self.assertNotIn(
            "harness-wakeup:f13f3552dc3d8ad812cc6f26e48e97eb8cad9791:bake",
            keep_post,
        )

    def test_local_bake_still_passes(self) -> None:
        saved = (wakeup.ROOT, wakeup.now, wakeup.ntfy)
        with tempfile.TemporaryDirectory(prefix="wakeup-leftover-") as tmp:
            os.makedirs(os.path.join(tmp, "wakeups"), exist_ok=True)
            job = {
                "from": "CODEX_LOCAL",
                "id": "codex-wakeup-leftover-33717474657",
                "wakeup": "2026-08-22T22:00:00Z",
                "adapter": "Codex/local/GitHub Actions",
            }
            with open(os.path.join(tmp, "wakeups", "CODEX_LOCAL.json"), "w", encoding="utf-8") as handle:
                json.dump(job, handle)
            wakeup.ROOT = tmp
            wakeup.ntfy = lambda _row, _attempt_id: True
            try:
                self.assertEqual(wakeup.main(), 0)
                with open(os.path.join(tmp, "wakeups", "fired.json"), encoding="utf-8") as handle:
                    fired = json.load(handle)
                self.assertIn("codex-wakeup-leftover-33717474657", fired.get("ids") or [])
                self.assertEqual(wakeup.main(), 0)
                with open(os.path.join(tmp, "wakeups.json"), encoding="utf-8") as handle:
                    public = json.load(handle)
            finally:
                wakeup.ROOT, wakeup.now, wakeup.ntfy = saved
        self.assertEqual(public.get("due"), [])
        self.assertIn("codex-wakeup-leftover-33717474657", public.get("fired") or [])

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "harness-wakeup.yml job bake executes python3 wakeup.py "
                "then lands wakeups.json and wakeups/fired.json on main"
            ),
            "repair_attempts": [
                "local test_wakeup_reliability.py 10/10",
                "local wakeup.py bake ntfy-mocked rc=0 due=0 fired=9",
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
