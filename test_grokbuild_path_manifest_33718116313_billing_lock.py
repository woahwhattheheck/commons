#!/usr/bin/env python3
"""Pin unique leftover for path-manifest run 33718116313. Do not remint classifier or prior leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-path-manifest-33718116313-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-path-manifest-33699980177-billing-lock-20260903-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_path_manifest_33699980177_billing_lock.py"
HARNESS = ROOT / "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md"
HARNESS_TEST = ROOT / "test_grokbuild_harness_wakeup_33717474657_billing_lock.py"

KEEP = {
    "test_path_manifest.py": "c6de797a",
    "host/path_manifest.py": "dcc94697",
    ".github/workflows/path-manifest.yml": "b29dec8a",
    "architecture/path-manifest.json": "e5ecb24f",
    "p/grokbuild-path-manifest-33717733938-billing-lock-20260903-01.md": "85a5f189",
    "test_grokbuild_path_manifest_33717733938_billing_lock.py": "992e84ca",
    "p/grokbuild-path-manifest-33699980177-billing-lock-20260903-01.md": "d9365b97",
    "test_grokbuild_path_manifest_33699980177_billing_lock.py": "4740e323",
    "p/grokbuild-path-manifest-33694214802-billing-lock-20260902-01.md": "d9331b17",
    "test_grokbuild_path_manifest_33694214802_billing_lock.py": "456e9d0d",
    "p/grokbuild-pr8415-path-manifest-33689243555-20260902-01.md": "3c72cd09",
    "test_grokbuild_pr8415_path_manifest_33689243555.py": "5494bffe",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "test_grokbuild_harness_wakeup_33717474657_billing_lock.py": "760a8169",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPathManifest33718116313BillingLock(unittest.TestCase):
    def test_keep_classifier_and_sibling_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = (ROOT / ".github/workflows/path-manifest.yml").read_text(encoding="utf-8")
        self.assertIn("python3 test_path_manifest.py", yml)
        self.assertIn("python3 host/path_manifest.py", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
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
                "test_grokbuild_path_manifest_33718116313_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-path-manifest-33718116313-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        harness = HARNESS.read_text(encoding="utf-8")
        harness_test = HARNESS_TEST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-path-manifest-33718116313-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:path-manifest:51814ebf019d53c42ec170b4ed626eb0036fc48e:observe",
            text,
        )
        self.assertIn("33718116313", text)
        self.assertIn("51814ebf019d53c42ec170b4ed626eb0036fc48e", text)
        self.assertIn("100531470261", text)
        self.assertIn("100532942869", text)
        self.assertIn("8584", text)
        self.assertIn("088e748c68bc7eada5027f5760175bcbd114be1f", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("c6de797a", text)
        self.assertIn("dcc94697", text)
        self.assertIn("b29dec8a", text)
        self.assertIn("e5ecb24f", text)
        self.assertIn("f54e1846", text)
        self.assertIn("760a8169", text)
        self.assertIn("85a5f189", text)
        self.assertIn("992e84ca", text)
        self.assertIn("d9365b97", text)
        self.assertIn("4740e323", text)
        self.assertIn("d9331b17", text)
        self.assertIn("456e9d0d", text)
        self.assertIn("3c72cd09", text)
        self.assertIn("5494bffe", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("4b053e43", text)
        self.assertIn("a0af1282", text)
        self.assertIn("f3afb926", text)
        self.assertIn("b7a4ea0e", text)
        self.assertIn("f33a76ef", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8584", text)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, harness)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), harness_test)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn(
            "path-manifest:51814ebf019d53c42ec170b4ed626eb0036fc48e:observe",
            sibling,
        )
        self.assertNotIn(
            "path-manifest:51814ebf019d53c42ec170b4ed626eb0036fc48e:observe",
            harness,
        )
        self.assertNotIn("33717733938", text.split("KEEP unread", 1)[0])

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
                "event SHA 51814ebf classifier blobs MATCH current main",
                "associated PR 8584 leftover f54e1846 unread; its tests 4/4",
                "github billing APIs 401/404; rerun_failed_jobs 201; attempt 2 job 100532942869 same billing lock",
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
