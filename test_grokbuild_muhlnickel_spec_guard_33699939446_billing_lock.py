#!/usr/bin/env python3
"""Pin unique leftover for muhlnickel-spec-guard run 33699939446. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-muhlnickel-spec-guard-33699939446-billing-lock-20260903-01.md"
PEER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33689347386-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grok-build-muhlnickel-spec-guard-33689243569-billing-lock-20260902-01.md"
LLMS = ROOT / "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-muhlnickel-spec-guard-33699600936-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/muhlnickel-spec-guard.yml"

KEEP = {
    "muhlnickel_spec_guard.py": "74423d71",
    "test_muhlnickel_spec_guard.py": "097742ec",
    ".github/workflows/muhlnickel-spec-guard.yml": "7886bdf1",
    "open_door_guard.py": "4b053e43",
    "p/grok-build-muhlnickel-spec-guard-33689243569-billing-lock-20260902-01.md": "7032fbcf",
    "p/grokbuild-muhlnickel-spec-guard-33689088442-billing-lock-20260902-01.md": "61a98ddd",
    "p/grokbuild-muhlnickel-spec-guard-33689347386-billing-lock-20260902-01.md": "2c08e8ab",
    "p/grokbuild-muhlnickel-spec-guard-33699600936-billing-lock-20260903-01.md": "e063cc7e",
    "test_grokbuild_muhlnickel_spec_guard_33689243569_billing_lock.py": "897ba184",
    "test_grokbuild_muhlnickel_spec_guard_33689088442_billing_lock.py": "afbc462a",
    "test_grokbuild_muhlnickel_spec_guard_33689347386_billing_lock.py": "07e46f6f",
    "test_grokbuild_muhlnickel_spec_guard_33699600936_billing_lock.py": "7098db31",
    "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md": "43c6e5cb",
    "test_grokbuild_llms_txt_33699286770_billing_lock.py": "fc9b6424",
    "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md": "d22e0707",
    "p/grok-build-job-watchdog-33699286811-billing-lock-20260903-01.md": "81092ec2",
    "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md": "e8d308ed",
    "p/grokbuild-local-compute-guard-33699607453-billing-lock-20260903-01.md": "5d89a9bf",
    "p/grokbuild-local-compute-guard-33699601000-billing-lock-20260903-01.md": "da198a83",
    "p/grokbuild-open-door-guard-33699607387-billing-lock-20260903-01.md": "32f69eaf",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
    "p/grokbuild-pr8525-verify-20260903-01.md": "3e36c93c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildMuhlnickelSpecGuard33699939446BillingLock(unittest.TestCase):
    def test_keep_guard_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 muhlnickel_spec_guard.py --base", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("billing", yml.lower())

    def test_local_failed_step_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "muhlnickel_spec_guard.py", "--base", "HEAD^", "--worktree"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("MUHLNICKEL SPEC GUARD: clean", proc.stdout)
        tests = subprocess.run(
            ["python3", "-m", "unittest", "test_muhlnickel_spec_guard"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(tests.returncode, 0, msg=tests.stdout + tests.stderr)
        self.assertIn("Ran 19 tests", tests.stderr + tests.stdout)

    def test_receipt_cites_run_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        peer = PEER.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        llms = LLMS.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        self.assertIn("grokbuild-muhlnickel-spec-guard-33699939446-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:muhlnickel-spec-guard:05fb712e6e3991cc3f88bc53115f69eac58822f9:guard",
            text,
        )
        self.assertIn("33699939446", text)
        self.assertIn("100476855463", text)
        self.assertIn("100478030258", text)
        self.assertIn("05fb712e6e3991cc3f88bc53115f69eac58822f9", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("74423d71", text)
        self.assertIn("097742ec", text)
        self.assertIn("7886bdf1", text)
        self.assertIn("7032fbcf", text)
        self.assertIn("61a98ddd", text)
        self.assertIn("2c08e8ab", text)
        self.assertIn("e063cc7e", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("Did not remint leftover grok-build-muhlnickel-spec-guard-33689243569-billing-lock-20260902-01", text)
        self.assertIn("leftover grokbuild-muhlnickel-spec-guard-33689347386-billing-lock-20260902-01", text)
        self.assertIn("leftover grokbuild-muhlnickel-spec-guard-33699600936-billing-lock-20260903-01", text)
        self.assertIn("leftover grok-build-llms-txt-33699286770-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, peer)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, llms)
        self.assertNotEqual(text, sibling)
        self.assertNotIn(
            "muhlnickel-spec-guard:05fb712e6e3991cc3f88bc53115f69eac58822f9:guard",
            peer,
        )
        self.assertNotIn(
            "muhlnickel-spec-guard:05fb712e6e3991cc3f88bc53115f69eac58822f9:guard",
            prior,
        )
        self.assertNotIn(
            "muhlnickel-spec-guard:05fb712e6e3991cc3f88bc53115f69eac58822f9:guard",
            llms,
        )
        self.assertNotIn(
            "muhlnickel-spec-guard:05fb712e6e3991cc3f88bc53115f69eac58822f9:guard",
            sibling,
        )
        self.assertNotIn("buy.stripe.com", text)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "muhlnickel-spec-guard.yml job guard executes "
                "python3 muhlnickel_spec_guard.py --base BASE --worktree "
                "on pull_request"
            ),
            "repair_attempts": [
                "local test_muhlnickel_spec_guard.py 19/19 PASS",
                "local muhlnickel_spec_guard.py --base HEAD^ --worktree CLEAN",
                "github rerun_failed_jobs; attempt 2 same billing refusal",
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
