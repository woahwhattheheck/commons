#!/usr/bin/env python3
"""Pin unique leftover for path-manifest run 33699939404. Do not remint prior leftover or classifier."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-path-manifest-33699939404-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-path-manifest-33694214802-billing-lock-20260902-01.md"
SIBLING = ROOT / "p/grokbuild-pr8415-path-manifest-33689243555-20260902-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_pr8415_path_manifest_33689243555.py"
ASSOCIATED = ROOT / "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md"
GOAT = ROOT / "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md"
VERIFY = ROOT / "p/grokbuild-pr8479-verify-20260902-01.md"
OPEN_DOOR = ROOT / "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/path-manifest.yml"

KEEP = {
    "test_path_manifest.py": "c6de797a",
    "host/path_manifest.py": "dcc94697",
    ".github/workflows/path-manifest.yml": "b29dec8a",
    "architecture/path-manifest.json": "e5ecb24f",
    "test_grokbuild_path_manifest_33694214802_billing_lock.py": "456e9d0d",
    "p/grokbuild-path-manifest-33694214802-billing-lock-20260902-01.md": "d9331b17",
    "test_grokbuild_pr8415_path_manifest_33689243555.py": "5494bffe",
    "p/grokbuild-pr8415-path-manifest-33689243555-20260902-01.md": "3c72cd09",
    "test_grokbuild_llms_txt_33699286770_billing_lock.py": "fc9b6424",
    "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md": "43c6e5cb",
    "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md": "865b3c95",
    "p/grokbuild-pr8479-verify-20260902-01.md": "658530be",
    "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md": "d22e0707",
    "test_grokbuild_open_door_guard_33699286785_billing_lock.py": "96ce49fa",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPathManifest33699939404BillingLock(unittest.TestCase):
    def test_keep_classifier_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 test_path_manifest.py", yml)
        self.assertIn("python3 host/path_manifest.py", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
        self.assertNotIn("self-hosted", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_local_failed_step_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_path_manifest"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 9 tests", proc.stderr + proc.stdout)
        added = [
            guard.AddedLine(
                "test_grokbuild_path_manifest_33699939404_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-path-manifest-33699939404-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        associated = ASSOCIATED.read_text(encoding="utf-8")
        goat = GOAT.read_text(encoding="utf-8")
        verify = VERIFY.read_text(encoding="utf-8")
        open_door = OPEN_DOOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-path-manifest-33699939404-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:path-manifest:05fb712e6e3991cc3f88bc53115f69eac58822f9:observe",
            text,
        )
        self.assertIn("33699939404", text)
        self.assertIn("05fb712e6e3991cc3f88bc53115f69eac58822f9", text)
        self.assertIn("100476855125", text)
        self.assertIn("100478293847", text)
        self.assertIn("33700388865", text)
        self.assertIn("/8528", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("c6de797a", text)
        self.assertIn("dcc94697", text)
        self.assertIn("b29dec8a", text)
        self.assertIn("e5ecb24f", text)
        self.assertIn("d9331b17", text)
        self.assertIn("456e9d0d", text)
        self.assertIn("3c72cd09", text)
        self.assertIn("5494bffe", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("fc9b6424", text)
        self.assertIn("865b3c95", text)
        self.assertIn("658530be", text)
        self.assertIn("d22e0707", text)
        self.assertIn("96ce49fa", text)
        self.assertIn("Did not remint leftover grokbuild-path-manifest-33694214802-billing-lock-20260902-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, associated)
        self.assertNotEqual(text, goat)
        self.assertNotEqual(text, verify)
        self.assertNotEqual(text, open_door)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotIn(
            "path-manifest:05fb712e6e3991cc3f88bc53115f69eac58822f9:observe",
            prior,
        )
        self.assertNotIn(
            "path-manifest:05fb712e6e3991cc3f88bc53115f69eac58822f9:observe",
            sibling,
        )
        self.assertNotIn(
            "path-manifest:05fb712e6e3991cc3f88bc53115f69eac58822f9:observe",
            associated,
        )
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("33694214802", text.split("KEEP unread", 1)[0])

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "path-manifest.yml job observe executes "
                "python3 test_path_manifest.py then "
                "python3 host/path_manifest.py --report on pull_request"
            ),
            "repair_attempts": [
                "local test_path_manifest.py 9/9 OK; host/path_manifest.py report OBSERVED",
                "event SHA 05fb712 classifier blobs MATCH current main",
                "github billing APIs 404/403; rerun_failed_jobs 201; attempt 2 job 100478293847 same billing lock",
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
