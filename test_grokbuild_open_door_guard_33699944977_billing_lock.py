#!/usr/bin/env python3
"""Pin unique leftover for open-door-guard run 33699944977. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-open-door-guard-33699944977-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-open-door-guard-33699607387-billing-lock-20260903-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_open_door_guard_33699607387_billing_lock.py"
TRIGGER = ROOT / "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md"
TRIGGER_TEST = ROOT / "test_grokbuild_llms_txt_33699286770_billing_lock.py"

KEEP = {
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33699607387-billing-lock-20260903-01.md": "32f69eaf",
    "test_grokbuild_open_door_guard_33699607387_billing_lock.py": "1e4899d8",
    "p/grokbuild-open-door-guard-33699600907-billing-lock-20260903-01.md": "810a233f",
    "test_grokbuild_open_door_guard_33699600907_billing_lock.py": "08019321",
    "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md": "43c6e5cb",
    "test_grokbuild_llms_txt_33699286770_billing_lock.py": "fc9b6424",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildOpenDoorGuard33699944977BillingLock(unittest.TestCase):
    def test_keep_guard_and_sibling_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_local_failed_step_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "test_open_door_guard.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("OPEN DOOR GUARD TEST:", proc.stdout)
        added = [
            guard.AddedLine(
                "test_grokbuild_open_door_guard_33699944977_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-open-door-guard-33699944977-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])
        trigger_added = [
            guard.AddedLine(
                "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md", 1, line
            )
            for line in TRIGGER.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(trigger_added), [])
        trigger_test_added = [
            guard.AddedLine(
                "test_grokbuild_llms_txt_33699286770_billing_lock.py", 1, line
            )
            for line in TRIGGER_TEST.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(trigger_test_added), [])

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-open-door-guard-33699944977-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:open-door-guard:886b8f8e727558d03da1a91125b50b3d439b4864:reject-added-locks",
            text,
        )
        self.assertIn("33699944977", text)
        self.assertIn("886b8f8e727558d03da1a91125b50b3d439b4864", text)
        self.assertIn("100476872714", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("4b053e43", text)
        self.assertIn("70ee5730", text)
        self.assertIn("32f69eaf", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("Did not remint", text)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("33699607387", text.split("KEEP unread", 1)[0])

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "open-door-guard.yml job reject-added-locks executes "
                "python3 open_door_guard.py --diff BASE HEAD then "
                "python3 test_open_door_guard.py on push to main"
            ),
            "repair_attempts": [
                "local open_door_guard.py --diff 60d5e8fa 886b8f8e PASS",
                "local test_open_door_guard.py PASS",
                "same contracts PASS on current origin/main",
                "adjacent test_open_door rc=0 OPEN / test_fix_first 6 / test_path_manifest 9 / test_source_parses 9",
                "github billing API 403/404; job 100476872714 runner_id=0 steps=[] logs 404 BlobNotFound",
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
