#!/usr/bin/env python3
"""Pin unique leftover for tests battery run 33699945008. Do not remint peer leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-33699945008-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-tests-33694253421-billing-lock-20260902-01.md"
SIBLING = ROOT / "p/grokbuild-tests-33694246830-billing-lock-20260902-01.md"
TRIGGER = ROOT / "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/tests.yml"

KEEP = {
    "p/grokbuild-tests-33694253421-billing-lock-20260902-01.md": "da396946",
    "test_grokbuild_tests_33694253421_billing_lock.py": "f3ce3fe0",
    "p/grokbuild-tests-33694246830-billing-lock-20260902-01.md": "b07d6192",
    "test_grokbuild_tests_33694246830_billing_lock.py": "fb6fc00d",
    "p/grokbuild-tests-battery-33689096444-billing-lock-20260902-01.md": "a7ff1feb",
    "test_grokbuild_tests_battery_33689096444_billing_lock.py": "fe16c208",
    "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md": "43c6e5cb",
    "test_grokbuild_llms_txt_33699286770_billing_lock.py": "fc9b6424",
    "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md": "865b3c95",
    "p/goat-pages-super-mcp-land-20260902-01.md": "171e0daa",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
    "catalog.html": "154b7b67",
    "boards.html": "3fa79f12",
    "hub_pages.py": "5ac12648",
    ".github/workflows/tests.yml": "8c2f2301",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTests33699945008BillingLock(unittest.TestCase):
    def test_keep_peer_leftovers_and_tests_yml_unread(self) -> None:
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
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)
        self.assertNotIn("continue-on-error", yml)

    def test_local_failed_step_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "test_subject_keep.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("ok   subject keep", proc.stdout + proc.stderr)
        added = [
            guard.AddedLine("test_grokbuild_tests_33699945008_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grokbuild-tests-33699945008-billing-lock-20260903-01.md", 1, line
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        trigger = TRIGGER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-tests-33699945008-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:886b8f8e727558d03da1a91125b50b3d439b4864:battery",
            text,
        )
        self.assertIn("33699945008", text)
        self.assertIn("100476874377", text)
        self.assertIn("100478190358", text)
        self.assertIn("886b8f8e727558d03da1a91125b50b3d439b4864", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("da396946", text)
        self.assertIn("b07d6192", text)
        self.assertIn("a7ff1feb", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("865b3c95", text)
        self.assertIn("171e0daa", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("154b7b67", text)
        self.assertIn("3fa79f12", text)
        self.assertIn("5ac12648", text)
        self.assertIn("8c2f2301", text)
        self.assertIn("4b053e43", text)
        self.assertIn("Did not remint leftover grokbuild-tests-33694253421-billing-lock-20260902-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, trigger)
        self.assertNotIn(
            "tests:886b8f8e727558d03da1a91125b50b3d439b4864:battery",
            prior,
        )
        self.assertNotIn(
            "tests:886b8f8e727558d03da1a91125b50b3d439b4864:battery",
            sibling,
        )
        self.assertNotIn(
            "tests:886b8f8e727558d03da1a91125b50b3d439b4864:battery",
            trigger,
        )
        self.assertIn("33694253421", prior)
        self.assertIn("33699286770", trigger)

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
                "inspected tests.yml KEEP 8c2f2301; no YAML defect, no billing skip",
                "local publisher inventory 15/15 PASS on current main",
                "test_fix_first.py 6/6; test_path_manifest.py 9/9; test_source_parses.py 9/9",
                "open_door_guard --diff PASS; test_open_door_guard.py PASS",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal runner_id=0",
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
