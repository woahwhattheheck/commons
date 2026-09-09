#!/usr/bin/env python3
"""Pin unique leftover for merged-branch-janitor run 33689280158. Do not remint prior leftover or janitor."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-janitor-33689280158-billing-lock-20260902-01.md"
PRIOR_JANITOR = ROOT / "p/grokbuild-janitor-absent-ref-422-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/merged-branch-janitor.yml"

KEEP = {
    "merged_branch_janitor.py": "4d8eff11",
    ".github/workflows/merged-branch-janitor.yml": "84530bf3",
    "test_merged_branch_janitor.py": "a2b62df3",
    "p/grokbuild-janitor-absent-ref-422-20260902-01.md": "ba96b336",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md": "594b5e71",
    "p/grok-build-llms-txt-33689096471-billing-lock-20260902-01.md": "e739b9cd",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildJanitor33689280158BillingLock(unittest.TestCase):
    def test_keep_janitor_and_prior_leftovers_unread(self) -> None:
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
        self.assertIn("python3 merged_branch_janitor.py", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("billing", yml.lower())
        src = (ROOT / "merged_branch_janitor.py").read_text(encoding="utf-8")
        self.assertIn("the merged same-repo head ref is gone", src)
        self.assertIn("already_absent", src)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR_JANITOR.read_text(encoding="utf-8")
        self.assertIn("grok-build-janitor-33689280158-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:merged-branch-janitor:98eeae83050a6e83effb1c5e52511ec8cf27bf68:delete-merged-branch",
            text,
        )
        self.assertIn("33689280158", text)
        self.assertIn("100444017867", text)
        self.assertIn("100446111727", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grokbuild-janitor-absent-ref-422-20260902-01", text)
        self.assertIn("ba96b336", text)
        self.assertIn("4d8eff11", text)
        self.assertIn("84530bf3", text)
        self.assertIn("did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn(
            "merged-branch-janitor:98eeae83050a6e83effb1c5e52511ec8cf27bf68:delete-merged-branch",
            prior,
        )

    def test_janitor_unit_contract_still_green(self) -> None:
        rc = subprocess.run(
            ["python3", "-m", "unittest", "test_merged_branch_janitor.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(rc.returncode, 0, rc.stderr or rc.stdout)
        out = (rc.stdout or "") + (rc.stderr or "")
        self.assertIn("Ran 10 tests", out)
        self.assertIn("OK", out)


if __name__ == "__main__":
    unittest.main()
