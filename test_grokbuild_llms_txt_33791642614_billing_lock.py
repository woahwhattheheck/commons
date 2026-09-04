#!/usr/bin/env python3
"""Pin unique leftover for llms-txt run 33791642614. Do not remint publisher or prior leftovers."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-llms-txt-33791642614-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-llms-txt-33723861225-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-llms-txt-33723638519-billing-lock-20260903-01.md"
ALARM = ROOT / "p/grokbuild-staleness-alarm-33767754124-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/llms-txt.yml"

KEEP = {
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "llms_txt.py": "83fc5ea9",
    "owner_pin.py": "76e19209",
    "test_llms_publish.py": "c07317be",
    "test_llms_pulse.py": "e79f7851",
    "test_baked_head_json.py": "71a53f96",
    "open_door_guard.py": "4b053e43",
    "p/grokbuild-llms-txt-33723861225-billing-lock-20260903-01.md": "09244cf3",
    "test_grokbuild_llms_txt_33723861225_billing_lock.py": "e6160e8b",
    "p/grokbuild-llms-txt-33723638519-billing-lock-20260903-01.md": "98285e08",
    "test_grokbuild_llms_txt_33723638519_billing_lock.py": "e9bdbda8",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grokbuild-staleness-alarm-33767754124-billing-lock-20260903-01.md": "49d0ad65",
    "test_grokbuild_staleness_alarm_33767754124_billing_lock.py": "64c6da04",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildLlmsTxt33791642614BillingLock(unittest.TestCase):
    def test_keep_publisher_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 llms_txt.py --publish", yml)
        self.assertIn("ref: main", yml)
        self.assertIn("group: llms-txt-main", yml)
        self.assertIn("cancel-in-progress: false", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)
        src = (ROOT / "llms_txt.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("GITHUB_ACTIONS") != "true"', src)
        self.assertIn("unsafe-context", src)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        alarm = ALARM.read_text(encoding="utf-8")
        self.assertIn("grokbuild-llms-txt-33791642614-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:llms-txt:f048f0d9df6ce23c13dcc4f086551f8ce35138aa:bake",
            text,
        )
        self.assertIn("33791642614", text)
        self.assertIn("100769387130", text)
        self.assertIn("100770719355", text)
        self.assertIn("f048f0d9df6ce23c13dcc4f086551f8ce35138aa", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grokbuild-llms-txt-33723861225-billing-lock-20260903-01", text)
        self.assertIn("09244cf3", text)
        self.assertIn("313df49a", text)
        self.assertIn("98285e08", text)
        self.assertIn("a35bd46e", text)
        self.assertIn("cf9c9f40", text)
        self.assertIn("49d0ad65", text)
        self.assertIn("64c6da04", text)
        self.assertIn("83fc5ea9", text)
        self.assertIn("d2182a3d", text)
        self.assertIn("76e19209", text)
        self.assertIn("c07317be", text)
        self.assertIn("e79f7851", text)
        self.assertIn("71a53f96", text)
        self.assertIn("4b053e43", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, alarm)
        self.assertNotIn(
            "llms-txt:f048f0d9df6ce23c13dcc4f086551f8ce35138aa:bake",
            prior,
        )
        self.assertNotIn(
            "llms-txt:f048f0d9df6ce23c13dcc4f086551f8ce35138aa:bake",
            sibling,
        )
        self.assertNotIn(
            "llms-txt:f048f0d9df6ce23c13dcc4f086551f8ce35138aa:bake",
            alarm,
        )

    def test_publish_still_refuses_outside_actions(self) -> None:
        env = os.environ.copy()
        env.pop("GITHUB_ACTIONS", None)
        rc = subprocess.run(
            ["python3", "llms_txt.py", "--publish"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertNotEqual(rc.returncode, 0)
        out = (rc.stdout or "") + (rc.stderr or "")
        self.assertIn("refused outside GitHub Actions", out)
        self.assertIn("unsafe-context", out)

    def test_local_bake_only_and_fix_first_external_blocker(self) -> None:
        generated = [
            "challenge.json",
            "change.md",
            "fresh.md",
            "head.json",
            "llms.txt",
            "peers.md",
            "pulse.json",
        ]

        def restore() -> None:
            subprocess.run(
                ["git", "checkout", "--", *generated],
                cwd=ROOT,
                check=False,
            )

        self.addCleanup(restore)
        proc = subprocess.run(
            ["python3", "llms_txt.py", "--bake-only"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("baked src=git HEAD p/", proc.stdout)
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "llms-txt.yml job bake executes python3 llms_txt.py --publish "
                "on schedule and push to main"
            ),
            "repair_attempts": [
                "local --bake-only PASS on current main (publisher KEEP 83fc5ea9)",
                "test_llms_publish.py ALL PASS; test_llms_pulse.py 4/4; test_baked_head_json.py 10/10",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal",
                "GitHub Actions billing unlock is owner/provider work; gmail billing-lock search empty",
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
