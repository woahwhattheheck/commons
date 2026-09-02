#!/usr/bin/env python3
"""Pin unique leftover for merged-branch-janitor run 33689096287. Do not remint the janitor."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fix_first
import merged_branch_janitor as janitor
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-merged-branch-janitor-33689096287-billing-lock-20260902-01.md"
SIBLING_422 = ROOT / "p/grokbuild-janitor-absent-ref-422-20260902-01.md"
SIBLING_ODG = ROOT / "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md"
MERGE_ON_PR = ROOT / "p/cursor-merge-on-pr-20260902-01.md"
READBACK = ROOT / "p/cursor-merge-on-pr-readback-20260902-01.md"

KEEP = {
    "merged_branch_janitor.py": "4d8eff11",
    "test_merged_branch_janitor.py": "a2b62df3",
    ".github/workflows/merged-branch-janitor.yml": "84530bf3",
    "p/grokbuild-janitor-absent-ref-422-20260902-01.md": "ba96b336",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
}

EVENT_8414 = {
    "repository": {
        "full_name": "woahwhattheheck/commons",
        "default_branch": "main",
    },
    "pull_request": {
        "merged": True,
        "number": 8414,
        "head": {
            "ref": "cursor/merge-on-pr-readback-fe10",
            "sha": "0675fb559de118427a4c37b3cc406fc9f4cc7b64",
            "repo": {"full_name": "woahwhattheheck/commons"},
        },
        "base": {
            "ref": "main",
            "sha": "f078829d8a45fefe9d501fed55bfe330056f1335",
            "repo": {"full_name": "woahwhattheheck/commons"},
        },
    },
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildMergedBranchJanitor33689096287BillingLock(unittest.TestCase):
    def test_keep_janitor_and_siblings_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_local_failed_step_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "-W", "error", "-m", "unittest", "test_merged_branch_janitor.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("OK", proc.stderr)
        added = [
            guard.AddedLine(Path(__file__).name, 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        self.assertEqual(
            janitor.branch_to_delete(EVENT_8414),
            ("woahwhattheheck/commons", "cursor/merge-on-pr-readback-fe10"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(json.dumps(EVENT_8414), encoding="utf-8")
            api = mock.Mock()
            api.delete_ref.return_value = "deleted"
            result = janitor.run(path, api)
        api.delete_ref.assert_called_once_with(
            "woahwhattheheck/commons", "cursor/merge-on-pr-readback-fe10"
        )
        self.assertIn("deleted merged branch", result)

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling_422 = SIBLING_422.read_text(encoding="utf-8")
        sibling_odg = SIBLING_ODG.read_text(encoding="utf-8")
        leftover = MERGE_ON_PR.read_text(encoding="utf-8")
        readback = READBACK.read_text(encoding="utf-8")
        self.assertIn("grokbuild-merged-branch-janitor-33689096287-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:merged-branch-janitor:0675fb559de118427a4c37b3cc406fc9f4cc7b64:delete-merged-branch",
            text,
        )
        self.assertIn("33689096287", text)
        self.assertIn("0675fb559de118427a4c37b3cc406fc9f4cc7b64", text)
        self.assertIn("100443450069", text)
        self.assertIn("100446512103", text)
        self.assertIn("The job was not started because your account is locked due to a billing issue.", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("4d8eff11", text)
        self.assertIn("a2b62df3", text)
        self.assertIn("84530bf3", text)
        self.assertIn("Did not remint", text)
        self.assertIn("cursor/merge-on-pr-readback-fe10", text)
        self.assertIn("/pull/8414", text)
        self.assertNotEqual(text, sibling_422)
        self.assertNotEqual(text, sibling_odg)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, readback)
        self.assertNotIn("buy.stripe.com", text)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "merged-branch-janitor.yml job delete-merged-branch starts on "
                "ubuntu-latest after pull_request_target closed+merged and runs "
                "python3 merged_branch_janitor.py from trusted base.sha"
            ),
            "repair_attempts": [
                "local test_merged_branch_janitor.py 10/10 OK",
                "local merged_branch_janitor.py deleted cursor/merge-on-pr-readback-fe10",
                "GET leftover branch HTTP 404 after local janitor",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal",
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
