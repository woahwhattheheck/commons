#!/usr/bin/env python3
"""Pin unique leftover for tests run 33699939421. Do not remint prior leftovers or tests.yml."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-33699939421-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-tests-33694253421-billing-lock-20260902-01.md"
PRIOR2 = ROOT / "p/grokbuild-tests-33694246830-billing-lock-20260902-01.md"
PRIOR3 = ROOT / "p/grokbuild-tests-33689281316-billing-lock-20260902-01.md"
ASSOC = ROOT / "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/tests.yml"

KEEP = {
    ".github/workflows/tests.yml": "8c2f2301",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    "fix_first.py": "a57aee1c",
    "p/grokbuild-tests-33694253421-billing-lock-20260902-01.md": "da396946",
    "test_grokbuild_tests_33694253421_billing_lock.py": "f3ce3fe0",
    "p/grokbuild-tests-33694246830-billing-lock-20260902-01.md": "b07d6192",
    "test_grokbuild_tests_33694246830_billing_lock.py": "fb6fc00d",
    "p/grokbuild-tests-33689281316-billing-lock-20260902-01.md": "3db0ab2e",
    "test_grokbuild_tests_33689281316_billing_lock.py": "66bc4ff5",
    "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md": "43c6e5cb",
    "test_grokbuild_llms_txt_33699286770_billing_lock.py": "fc9b6424",
    "p/grok-build-llms-txt-33694402716-billing-lock-20260902-01.md": "6a8728e3",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
    "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md": "865b3c95",
    "catalog.html": "154b7b67",
    "boards.html": "3fa79f12",
    "hub_pages.py": "5ac12648",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTests33699939421BillingLock(unittest.TestCase):
    def test_keep_workflow_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: tests", yml)
        self.assertIn("battery:", yml)
        self.assertIn("the whole battery, one failure fails the run", yml)
        self.assertIn("find . -maxdepth 1 -type f -name 'test_*.py'", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)
        self.assertNotIn("continue-on-error", yml)

    def test_local_failed_step_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "test_grokbuild_llms_txt_33699286770_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, msg=out)
        self.assertIn("Ran 4 tests", out)
        self.assertIn("OK", out)
        added = [
            guard.AddedLine("test_grokbuild_tests_33699939421_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grokbuild-tests-33699939421-billing-lock-20260903-01.md", 1, line
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        prior2 = PRIOR2.read_text(encoding="utf-8")
        prior3 = PRIOR3.read_text(encoding="utf-8")
        assoc = ASSOC.read_text(encoding="utf-8")
        self.assertIn("grokbuild-tests-33699939421-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:05fb712e6e3991cc3f88bc53115f69eac58822f9:battery",
            text,
        )
        self.assertIn("33699939421", text)
        self.assertIn("100476855374", text)
        self.assertIn("100478486204", text)
        self.assertIn("05fb712e6e3991cc3f88bc53115f69eac58822f9", text)
        self.assertIn("886b8f8e727558d03da1a91125b50b3d439b4864", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("da396946", text)
        self.assertIn("b07d6192", text)
        self.assertIn("3db0ab2e", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("6a8728e3", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("865b3c95", text)
        self.assertIn("8c2f2301", text)
        self.assertIn("Did not remint leftover grokbuild-tests-33694253421-billing-lock-20260902-01", text)
        self.assertIn("Did not remint leftover grokbuild-tests-33694246830-billing-lock-20260902-01", text)
        self.assertIn("Did not remint leftover grokbuild-tests-33689281316-billing-lock-20260902-01", text)
        self.assertIn("Did not remint leftover grok-build-llms-txt-33699286770-billing-lock-20260903-01", text)
        self.assertIn("Did not remint leftover grok-build-llms-txt-33694402716-billing-lock-20260902-01", text)
        self.assertIn("did not reopen #7915", text.lower())
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, prior2)
        self.assertNotEqual(text, prior3)
        self.assertNotEqual(text, assoc)
        self.assertNotIn(
            "woahwhattheheck/commons:tests:05fb712e6e3991cc3f88bc53115f69eac58822f9:battery",
            prior,
        )
        self.assertNotIn(
            "woahwhattheheck/commons:tests:05fb712e6e3991cc3f88bc53115f69eac58822f9:battery",
            assoc,
        )
        self.assertNotIn("33699939421", prior)
        self.assertNotIn("33699939421", assoc)
        self.assertNotIn("buy.stripe.com", text)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "tests.yml job battery checks out the repo and runs every "
                "discovered root test_*.py / test_*.js plus infra test_*.py "
                "on push to main that touches engine or test paths"
            ),
            "repair_attempts": [
                "inspected tests.yml: valid battery, no skip",
                "local test_grokbuild_llms_txt_33699286770_billing_lock.py 4/4",
                "local test_path_manifest.py 9/9",
                "local test_source_parses.py 9/9",
                "local test_fix_first.py 6/6",
                "local test_open_door_guard.py PASS; open_door_guard.py --diff PASS",
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
