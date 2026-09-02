#!/usr/bin/env python3
"""Pin unique leftover for local-compute-guard run 33694253447. Do not remint prior leftover or guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import local_compute_guard as guard
import open_door_guard as door

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-local-compute-guard-33694253447-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grok-build-local-compute-guard-billing-lock-20260902-01.md"
PRIOR_338 = ROOT / "p/grok-build-local-compute-guard-33689281338-billing-lock-20260902-01.md"
PRIOR_241 = ROOT / "p/grokbuild-local-compute-guard-33689357241-billing-lock-20260902-01.md"
GOAT = ROOT / "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/local-compute-guard.yml"

KEEP = {
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-build-local-compute-guard-33689281338-billing-lock-20260902-01.md": "a33a1c81",
    "p/grokbuild-local-compute-guard-33689357241-billing-lock-20260902-01.md": "2517b71d",
    "p/goat-pages-super-mcp-land-20260902-01.md": "171e0daaf",
    "catalog.html": "154b7b67",
    "boards.html": "3fa79f12",
    "hub_pages.py": "5ac12648",
    "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md": "865b3c95",
    "test_cursor_goat_pages_super_mcp_land_readback_match.py": "1249f69e",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "local_compute_guard.py": "6be242af",
    "test_local_compute_guard.py": "b8d65280",
    ".github/workflows/local-compute-guard.yml": "9750c6a1",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildLocalComputeGuard33694253447BillingLock(unittest.TestCase):
    def test_keep_guard_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 local_compute_guard.py", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
        self.assertNotIn("self-hosted", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_local_failed_step_still_passes(self) -> None:
        self.assertEqual(guard.validate(), [])
        proc = subprocess.run(
            ["python3", "local_compute_guard.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("CLOUD_PRIMARY / SAFE_STANDBY", proc.stdout)
        tests = subprocess.run(
            ["python3", "-m", "unittest", "test_local_compute_guard"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(tests.returncode, 0, msg=tests.stdout + tests.stderr)
        self.assertIn("Ran 2 tests", tests.stderr + tests.stdout)
        added = [
            door.AddedLine(
                "test_grokbuild_local_compute_guard_33694253447_billing_lock.py",
                1,
                line,
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(door.scan_added(added), [])
        receipt_added = [
            door.AddedLine(str(RECEIPT.relative_to(ROOT)), 1, line)
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(door.scan_added(receipt_added), [])

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        prior_338 = PRIOR_338.read_text(encoding="utf-8")
        prior_241 = PRIOR_241.read_text(encoding="utf-8")
        goat = GOAT.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-local-compute-guard-33694253447-billing-lock-20260902-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons:local-compute-guard:1fb31f62c6af944f339ced5665446891a91c95cd:placement",
            text,
        )
        self.assertIn("33694253447", text)
        self.assertIn("100459584399", text)
        self.assertIn("100461425995", text)
        self.assertIn("1fb31f62c6af944f339ced5665446891a91c95cd", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-local-compute-guard-billing-lock-20260902-01", text)
        self.assertIn("de59bf75", text)
        self.assertIn("a33a1c81", text)
        self.assertIn("2517b71d", text)
        self.assertIn("171e0daaf", text)
        self.assertIn("154b7b67", text)
        self.assertIn("3fa79f12", text)
        self.assertIn("5ac12648", text)
        self.assertIn("6be242af", text)
        self.assertIn("b8d65280", text)
        self.assertIn("9750c6a1", text)
        self.assertIn("did not reopen #7915", text)
        self.assertIn("/8479", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, prior_338)
        self.assertNotEqual(text, prior_241)
        self.assertNotEqual(text, goat)
        self.assertNotIn(
            "local-compute-guard:1fb31f62c6af944f339ced5665446891a91c95cd:placement",
            prior,
        )
        self.assertNotIn(
            "local-compute-guard:1fb31f62c6af944f339ced5665446891a91c95cd:placement",
            prior_338,
        )
        self.assertNotIn(
            "local-compute-guard:1fb31f62c6af944f339ced5665446891a91c95cd:placement",
            prior_241,
        )

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "local-compute-guard.yml job placement executes "
                "python3 local_compute_guard.py on push to main"
            ),
            "repair_attempts": [
                "local python3 local_compute_guard.py CLOUD_PRIMARY / SAFE_STANDBY exit 0",
                "local test_local_compute_guard.py 2/2 PASS",
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
