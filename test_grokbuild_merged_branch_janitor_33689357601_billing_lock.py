#!/usr/bin/env python3
"""Pin unique leftover for janitor run 33689357601. Do not remint janitor source."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import fix_first
import merged_branch_janitor as janitor

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-merged-branch-janitor-33689357601-billing-lock-20260902-01.md"
SIBLING_890 = ROOT / "p/grokbuild-merged-branch-janitor-33689096287-billing-lock-20260902-01.md"
SIBLING_80158 = ROOT / "p/grok-build-janitor-33689280158-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/merged-branch-janitor.yml"
PR8409 = ROOT / "p/grokbuild-pr8409-verify-20260902-01.md"

KEEP = {
    "merged_branch_janitor.py": "4d8eff11",
    "test_merged_branch_janitor.py": "a2b62df3",
    ".github/workflows/merged-branch-janitor.yml": "84530bf3",
    "p/grokbuild-janitor-absent-ref-422-20260902-01.md": "ba96b336",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "p/grokbuild-pr8409-verify-20260902-01.md": "199cc075",
    "p/grokbuild-merged-branch-janitor-33689096287-billing-lock-20260902-01.md": "c681ae82",
    "p/grok-build-janitor-33689280158-billing-lock-20260902-01.md": "4d965d51",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildMergedBranchJanitor33689357601BillingLock(unittest.TestCase):
    def test_keep_janitor_and_sibling_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", yml)
        self.assertIn("types: [closed]", yml)
        self.assertIn("ref: ${{ github.event.pull_request.base.sha }}", yml)
        self.assertNotIn("github.event.pull_request.head.sha", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("continue-on-error", yml)
        self.assertNotIn("billing", yml.lower())

    def test_local_failed_step_still_passes_for_this_pr_event(self) -> None:
        event = {
            "repository": {
                "full_name": "woahwhattheheck/commons",
                "default_branch": "main",
            },
            "pull_request": {
                "number": 8416,
                "merged": True,
                "head": {
                    "ref": "grokbuild/pr8409-verify-20260902-01",
                    "sha": "718682437ac745edaadd304b8199f28af3c4ad6d",
                    "repo": {"full_name": "woahwhattheheck/commons"},
                },
                "base": {
                    "ref": "main",
                    "sha": "81e8f9ccc7293bf6e5179e615ba460d87f409eb0",
                    "repo": {"full_name": "woahwhattheheck/commons"},
                },
            },
        }
        self.assertEqual(
            janitor.branch_to_delete(event),
            ("woahwhattheheck/commons", "grokbuild/pr8409-verify-20260902-01"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(json.dumps(event), encoding="utf-8")

            class FakeAPI:
                def delete_ref(self, repository, branch):
                    self.deleted = (repository, branch)
                    return "deleted"

            api = FakeAPI()
            result = janitor.run(path, api)
        self.assertEqual(
            api.deleted,
            ("woahwhattheheck/commons", "grokbuild/pr8409-verify-20260902-01"),
        )
        self.assertIn("deleted merged branch", result)
        proc = subprocess.run(
            ["python3", "-W", "error", "-m", "unittest", "test_merged_branch_janitor.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 10 tests", proc.stderr)

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling_890 = SIBLING_890.read_text(encoding="utf-8")
        sibling_80158 = SIBLING_80158.read_text(encoding="utf-8")
        pr8409 = PR8409.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-merged-branch-janitor-33689357601-billing-lock-20260902-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons:merged-branch-janitor:718682437ac745edaadd304b8199f28af3c4ad6d:delete-merged-branch",
            text,
        )
        self.assertIn("33689357601", text)
        self.assertIn("100444266025", text)
        self.assertIn("100447231232", text)
        self.assertIn("718682437ac745edaadd304b8199f28af3c4ad6d", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("4d8eff11", text)
        self.assertIn("a2b62df3", text)
        self.assertIn("84530bf3", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("c681ae82", text)
        self.assertIn("4d965d51", text)
        self.assertIn("Git Data", text)
        self.assertIn("grokbuild/pr8409-verify-20260902-01", text)
        self.assertNotEqual(text, sibling_890)
        self.assertNotEqual(text, sibling_80158)
        self.assertNotEqual(text, pr8409)
        self.assertNotIn(
            "merged-branch-janitor:718682437ac745edaadd304b8199f28af3c4ad6d:delete-merged-branch",
            sibling_890,
        )
        self.assertNotIn("33689357601", sibling_890)
        self.assertNotIn("33689357601", sibling_80158)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "merged-branch-janitor.yml job delete-merged-branch executes "
                "python3 merged_branch_janitor.py after a merged same-repo PR "
                "close so the head ref is gone"
            ),
            "repair_attempts": [
                "local unittest test_merged_branch_janitor.py 10/10",
                "PR 8416 event eligible; FakeAPI would delete grokbuild/pr8409-verify-20260902-01",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal runner_id=0",
                "Git Data DELETE leftover merged ref; subsequent GET HTTP 404",
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
