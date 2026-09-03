#!/usr/bin/env python3
"""Pin unique leftover for llms-txt run 33723861225. Do not remint publisher or prior leftovers."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-llms-txt-33723861225-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grok-build-llms-txt-billing-lock-20260902-01.md"
PRIOR_RUN = ROOT / "p/grokbuild-llms-txt-33718131457-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grok-build-llms-txt-33699940559-billing-lock-20260903-01.md"
TRIGGER = ROOT / "p/grok-build-commons-board-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/llms-txt.yml"

KEEP = {
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-33689083252-billing-lock-20260902-01.md": "31213531",
    "p/grok-build-llms-txt-33689096471-billing-lock-20260902-01.md": "e739b9cd",
    "p/grok-build-llms-txt-33689281224-billing-lock-20260902-01.md": "e710946d",
    "p/grok-build-llms-txt-33689357433-billing-lock-20260902-01.md": "d103be4c",
    "p/grok-build-llms-txt-33694219034-billing-lock-20260902-01.md": "d8f8b166",
    "p/grok-build-llms-txt-33694253456-billing-lock-20260902-01.md": "8e08896c",
    "p/grok-build-llms-txt-33694402716-billing-lock-20260902-01.md": "6a8728e3",
    "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md": "43c6e5cb",
    "p/grok-build-llms-txt-33699607384-billing-lock-20260903-01.md": "214368d9",
    "p/grok-build-llms-txt-33699940559-billing-lock-20260903-01.md": "44411b3e",
    "p/grokbuild-llms-txt-33718131457-billing-lock-20260903-01.md": "d87fe8da",
    "test_grokbuild_llms_txt_33718131457_billing_lock.py": "6d35c0d8",
    "p/grok-build-commons-board-billing-lock-20260903-01.md": "c07bf913",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "test_grokbuild_harness_wakeup_33717474657_billing_lock.py": "760a8169",
    "p/grokbuild-slack-service-tags-33717615004-billing-lock-20260903-01.md": "f33a76ef",
    "test_grokbuild_slack_service_tags_33717615004_billing_lock.py": "e10a1435",
    "p/grokbuild-open-door-guard-33717733987-billing-lock-20260903-01.md": "a0af1282",
    "test_grokbuild_open_door_guard_33717733987_billing_lock.py": "0269ac73",
    "p/grokbuild-path-manifest-33717733938-billing-lock-20260903-01.md": "85a5f189",
    "test_grokbuild_path_manifest_33717733938_billing_lock.py": "992e84ca",
    "p/grok-build-job-watchdog-33717741080-billing-lock-20260903-01.md": "f3afb926",
    "test_grokbuild_job_watchdog_33717741080_billing_lock.py": "7a1bc6f6",
    "p/grok-build-discord-cloud-33717741051-billing-lock-20260903-01.md": "b7a4ea0e",
    "test_grokbuild_discord_cloud_33717741051_billing_lock.py": "361b7c4b",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
    "p/latch-hub-eyes-wake-habit-20260902-01.md": "dc83d42c",
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "llms_txt.py": "83fc5ea9",
    "owner_pin.py": "76e19209",
    "test_llms_publish.py": "c07317be",
    "test_llms_pulse.py": "e79f7851",
    "open_door_guard.py": "4b053e43",
    "test_grokbuild_llms_txt_billing_lock.py": "6d73d3f9",
    "test_grokbuild_llms_txt_33699940559_billing_lock.py": "4a110ed3",
    "test_grokbuild_llms_txt_33699607384_billing_lock.py": "23b25bab",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildLlmsTxt33723861225BillingLock(unittest.TestCase):
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
        prior_run = PRIOR_RUN.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        trigger = TRIGGER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-llms-txt-33723861225-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:llms-txt:f0a980053dae781f35e8723428d42aae64b7a5d3:bake",
            text,
        )
        self.assertIn("33723861225", text)
        self.assertIn("100548468022", text)
        self.assertIn("100549675792", text)
        self.assertIn("f0a980053dae781f35e8723428d42aae64b7a5d3", text)
        self.assertIn("09c5ba16b592f1bf5c618e7fb1f48bbe36d16ed4", text)
        self.assertIn("8635", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("c697ab32-001e-000b-056e-3b6c9a000000", text)
        self.assertIn("f30af36e-e01e-0085-1e6f-3bb559000000", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-llms-txt-billing-lock-20260902-01", text)
        self.assertIn("cf9c9f40", text)
        self.assertIn("3183564c", text)
        self.assertIn("31213531", text)
        self.assertIn("e739b9cd", text)
        self.assertIn("e710946d", text)
        self.assertIn("d103be4c", text)
        self.assertIn("d8f8b166", text)
        self.assertIn("8e08896c", text)
        self.assertIn("6a8728e3", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("214368d9", text)
        self.assertIn("44411b3e", text)
        self.assertIn("d87fe8da", text)
        self.assertIn("6d35c0d8", text)
        self.assertIn("c07bf913", text)
        self.assertIn("f54e1846", text)
        self.assertIn("760a8169", text)
        self.assertIn("f33a76ef", text)
        self.assertIn("e10a1435", text)
        self.assertIn("a0af1282", text)
        self.assertIn("0269ac73", text)
        self.assertIn("85a5f189", text)
        self.assertIn("992e84ca", text)
        self.assertIn("f3afb926", text)
        self.assertIn("7a1bc6f6", text)
        self.assertIn("b7a4ea0e", text)
        self.assertIn("361b7c4b", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("dc83d42c", text)
        self.assertIn("83fc5ea9", text)
        self.assertIn("d2182a3d", text)
        self.assertIn("76e19209", text)
        self.assertIn("c07317be", text)
        self.assertIn("e79f7851", text)
        self.assertIn("4b053e43", text)
        self.assertIn("d4c58153", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, prior_run)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, trigger)
        self.assertNotIn(
            "llms-txt:f0a980053dae781f35e8723428d42aae64b7a5d3:bake",
            prior,
        )
        self.assertNotIn(
            "llms-txt:f0a980053dae781f35e8723428d42aae64b7a5d3:bake",
            prior_run,
        )
        self.assertNotIn(
            "llms-txt:f0a980053dae781f35e8723428d42aae64b7a5d3:bake",
            sibling,
        )
        self.assertNotIn(
            "llms-txt:f0a980053dae781f35e8723428d42aae64b7a5d3:bake",
            trigger,
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
                "on push to main"
            ),
            "repair_attempts": [
                "local --bake-only PASS on current main (publisher KEEP 83fc5ea9)",
                "test_llms_publish.py ALL PASS; test_llms_pulse.py 4/4; test_baked_head_json.py 10/10",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal",
                "later main runs 33724047446 / 33724086369 / 33724210371 / 33724230262 same billing refusal",
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
