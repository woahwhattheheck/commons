#!/usr/bin/env python3
"""Pin grok-build terminal leftover for already-merged PR 8415 path-manifest. Do not remint 8411 leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8415-path-manifest-33689243555-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-pr8411-verify-20260902-01.md"
ORIGINAL = ROOT / "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md"

KEEP = {
    "p/grokbuild-pr8411-verify-20260902-01.md": "642dea64",
    "test_grokbuild_pr8411_verify.py": "361f5ca1",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "test_grokbuild_llms_txt_33687829181_billing_lock.py": "e02e5ab5",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "llms_txt.py": "83fc5ea9",
}

BODY_SHA256 = "663d15bcecbfc310ea47e055d32a975e3097eaabc942bb2eed8a4a7da5f94543"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def receipt_body(text: str) -> str:
    parts = text.split("---\n", 2)
    return parts[2].rstrip("\n") if len(parts) >= 3 else text


class TestGrokbuildPr8415PathManifest(unittest.TestCase):
    def test_keep_8415_and_8411_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_8411_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_pr8411_verify"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 2 tests", proc.stderr + proc.stdout)

    def test_path_manifest_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_path_manifest"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 9 tests", proc.stderr + proc.stdout)

    def test_receipt_cites_8415_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        original = ORIGINAL.read_text(encoding="utf-8")
        body = receipt_body(text)
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)
        self.assertIn("grokbuild-pr8415-path-manifest-33689243555-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:path-manifest:98eeae83050a6e83effb1c5e52511ec8cf27bf68:observe",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8415", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/actions/runs/33689243555", text)
        self.assertIn("100443908791", text)
        self.assertIn("issuecomment-5517254284", text)
        self.assertIn("81e8f9ccc7293bf6e5179e615ba460d87f409eb0", text)
        self.assertIn("98eeae83050a6e83effb1c5e52511ec8cf27bf68", text)
        self.assertIn("642dea64", text)
        self.assertIn("3183564c", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("account locked due to a billing issue", text)
        self.assertIn("runner_id=0", text)
        self.assertIn("get_job_logs HTTP 404", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8415-path-manifest-33689243555-20260902-01", prior)


if __name__ == "__main__":
    unittest.main()
