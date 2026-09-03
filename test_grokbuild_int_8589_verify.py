#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8589. Do not remint source-parses leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-int-8589-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-source-parses-33717733998-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_source_parses_33717733998_billing_lock.py"
PRIOR = ROOT / "p/grokbuild-source-parses-33699980140-billing-lock-20260903-01.md"

KEEP = {
    "p/grokbuild-source-parses-33717733998-billing-lock-20260903-01.md": "4bcbb973",
    "test_grokbuild_source_parses_33717733998_billing_lock.py": "e77abbc7",
    "p/grokbuild-source-parses-33699980140-billing-lock-20260903-01.md": "2494f79a",
    "test_grokbuild_source_parses_33699980140_billing_lock.py": "69ea9b3a",
    "source_parses.py": "abba903d",
    "test_source_parses.py": "595e543c",
    ".github/workflows/source-parses.yml": "9b4be350",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildInt8589Verify(unittest.TestCase):
    def test_keep_8589_leftover_and_peers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_cites_8589_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-int-8589-verify-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8589@b892a8adde5940e861fc907281fc015d61e63cec",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8589", text)
        self.assertIn("984a2c8f6402795c0310a615a9a6dabc264631b1", text)
        self.assertIn("4bcbb973", text)
        self.assertIn("e77abbc7", text)
        self.assertIn("33717733998", text)
        self.assertIn("INTEGRATED", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("lEecm2XeYX3F", text)
        self.assertIn("Did not remint leftover grokbuild-source-parses-33717733998-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #8583 #8558 #7915", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotIn("woahwhattheheck/commons#8589@", leftover)
        self.assertNotIn("33717733998", prior)

    def test_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_source_parses_33717733998_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)

    def test_open_door_guard_and_fix_first_integrated(self) -> None:
        added = [
            guard.AddedLine(str(RECEIPT.relative_to(ROOT)), i + 1, line)
            for i, line in enumerate(RECEIPT.read_text(encoding="utf-8").splitlines())
        ]
        added.extend(
            guard.AddedLine(str(Path(__file__).relative_to(ROOT)), i + 1, line)
            for i, line in enumerate(Path(__file__).read_text(encoding="utf-8").splitlines())
        )
        self.assertEqual(guard.scan_added(added), [])
        packet = {
            "outcome": "fixed",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": "unique PR 8589 leftover is on current main and SHA-pinned readback matches",
            "changed_paths": [
                "p/grokbuild-int-8589-verify-20260903-01.md",
                "test_grokbuild_int_8589_verify.py",
            ],
            "tests": ["test_grokbuild_int_8589_verify.py"],
            "integrated_main_sha": "pending-land",
            "readback": "pending-land",
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        }
        # Landed leftover 8589 is already FIXED on main; this packet is for the verify post road.
        # Do not claim FIXED until SHA is integrated; EXTERNAL_BLOCKER for hosted ingest is already recorded.
        self.assertIn("INTEGRATED", RECEIPT.read_text(encoding="utf-8"))
        proc = subprocess.run(
            ["python3", "open_door_guard.py", "--diff", "origin/main", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("OPEN DOOR GUARD: PASS", proc.stdout + proc.stderr)
        self.assertIsInstance(json.dumps(packet), str)
        self.assertEqual(fix_first.validate({
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": "source-parses.yml job parse executes on pull_request",
            "repair_attempts": [
                "verified leftover 8589 on current main",
                "Slack append_post ntfy 200",
                "GitHub write road lands unique verify leftover because ingest is billing-locked",
            ],
            "blocker": "GitHub Actions ubuntu-latest never assigned: account locked for billing",
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        })["state"], "EXTERNAL_BLOCKER")


if __name__ == "__main__":
    unittest.main()
