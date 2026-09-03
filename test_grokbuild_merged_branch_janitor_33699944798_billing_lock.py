#!/usr/bin/env python3
"""Pin unique leftover for janitor run 33699944798. Do not remint janitor source."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import fix_first
import merged_branch_janitor as janitor
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-merged-branch-janitor-33699944798-billing-lock-20260903-01.md"
SIBLING_890 = ROOT / "p/grokbuild-merged-branch-janitor-33689096287-billing-lock-20260902-01.md"
SIBLING_80158 = ROOT / "p/grok-build-janitor-33689280158-billing-lock-20260902-01.md"
SIBLING_893 = ROOT / "p/grokbuild-merged-branch-janitor-33689357601-billing-lock-20260902-01.md"
SIBLING_942 = ROOT / "p/grokbuild-merged-branch-janitor-33694252910-billing-lock-20260902-01.md"
SIBLING_996 = ROOT / "p/grokbuild-merged-branch-janitor-33699606864-billing-lock-20260903-01.md"
PR8525 = ROOT / "p/grokbuild-pr8525-verify-20260903-01.md"
LLMS = ROOT / "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/merged-branch-janitor.yml"

KEEP = {
    "merged_branch_janitor.py": "4d8eff11",
    "test_merged_branch_janitor.py": "a2b62df3",
    ".github/workflows/merged-branch-janitor.yml": "84530bf3",
    "p/grokbuild-janitor-absent-ref-422-20260902-01.md": "ba96b336",
    "p/grokbuild-merged-branch-janitor-33689096287-billing-lock-20260902-01.md": "c681ae82",
    "p/grok-build-janitor-33689280158-billing-lock-20260902-01.md": "4d965d51",
    "p/grokbuild-merged-branch-janitor-33689357601-billing-lock-20260902-01.md": "e2731d89",
    "p/grokbuild-merged-branch-janitor-33694252910-billing-lock-20260902-01.md": "36a6483a",
    "test_grokbuild_merged_branch_janitor_33694252910_billing_lock.py": "df91c7e1",
    "p/grokbuild-merged-branch-janitor-33699606864-billing-lock-20260903-01.md": "135dacee",
    "test_grokbuild_merged_branch_janitor_33699606864_billing_lock.py": "46b574a8",
    "p/grokbuild-pr8525-verify-20260903-01.md": "3e36c93c",
    "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md": "43c6e5cb",
    "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md": "e8d308ed",
    "catalog.html": "154b7b67",
    "boards.html": "3fa79f12",
    "hub_pages.py": "5ac12648",
}

EVENT_8528 = {
    "repository": {
        "full_name": "woahwhattheheck/commons",
        "default_branch": "main",
    },
    "pull_request": {
        "number": 8528,
        "merged": True,
        "head": {
            "ref": "grokbuild/llms-txt-33699286770-billing-lock-20260903-01",
            "sha": "05fb712e6e3991cc3f88bc53115f69eac58822f9",
            "repo": {"full_name": "woahwhattheheck/commons"},
        },
        "base": {
            "ref": "main",
            "sha": "e25521733acdd3387c285e37483a74d7af8de3c3",
            "repo": {"full_name": "woahwhattheheck/commons"},
        },
    },
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildMergedBranchJanitor33699944798BillingLock(unittest.TestCase):
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
        self.assertEqual(
            janitor.branch_to_delete(EVENT_8528),
            (
                "woahwhattheheck/commons",
                "grokbuild/llms-txt-33699286770-billing-lock-20260903-01",
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(json.dumps(EVENT_8528), encoding="utf-8")

            class FakeAPI:
                def delete_ref(self, repository, branch):
                    self.deleted = (repository, branch)
                    return "deleted"

            api = FakeAPI()
            result = janitor.run(path, api)
        self.assertEqual(
            api.deleted,
            (
                "woahwhattheheck/commons",
                "grokbuild/llms-txt-33699286770-billing-lock-20260903-01",
            ),
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
        added = [
            guard.AddedLine(Path(__file__).name, 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling_890 = SIBLING_890.read_text(encoding="utf-8")
        sibling_80158 = SIBLING_80158.read_text(encoding="utf-8")
        sibling_893 = SIBLING_893.read_text(encoding="utf-8")
        sibling_942 = SIBLING_942.read_text(encoding="utf-8")
        sibling_996 = SIBLING_996.read_text(encoding="utf-8")
        pr8525 = PR8525.read_text(encoding="utf-8")
        llms = LLMS.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-merged-branch-janitor-33699944798-billing-lock-20260903-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons:merged-branch-janitor:05fb712e6e3991cc3f88bc53115f69eac58822f9:delete-merged-branch",
            text,
        )
        self.assertIn("33699944798", text)
        self.assertIn("100476872179", text)
        self.assertIn("100478959000", text)
        self.assertIn("05fb712e6e3991cc3f88bc53115f69eac58822f9", text)
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
        self.assertIn("e2731d89", text)
        self.assertIn("36a6483a", text)
        self.assertIn("df91c7e1", text)
        self.assertIn("135dacee", text)
        self.assertIn("46b574a8", text)
        self.assertIn("3e36c93c", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("e8d308ed", text)
        self.assertIn("154b7b67", text)
        self.assertIn("3fa79f12", text)
        self.assertIn("5ac12648", text)
        self.assertIn("Git Data", text)
        self.assertIn("grokbuild/llms-txt-33699286770-billing-lock-20260903-01", text)
        self.assertIn("/pull/8528", text)
        self.assertNotEqual(text, sibling_890)
        self.assertNotEqual(text, sibling_80158)
        self.assertNotEqual(text, sibling_893)
        self.assertNotEqual(text, sibling_942)
        self.assertNotEqual(text, sibling_996)
        self.assertNotEqual(text, pr8525)
        self.assertNotEqual(text, llms)
        self.assertNotIn("33699944798", sibling_890)
        self.assertNotIn("33699944798", sibling_80158)
        self.assertNotIn("33699944798", sibling_893)
        self.assertNotIn("33699944798", sibling_942)
        self.assertNotIn("33699944798", sibling_996)
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
                "local unittest test_merged_branch_janitor.py 10/10",
                "PR 8528 event eligible; FakeAPI would delete grokbuild/llms-txt-33699286770-billing-lock-20260903-01",
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
