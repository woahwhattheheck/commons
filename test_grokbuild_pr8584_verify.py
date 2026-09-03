#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8584. Do not remint harness-wakeup leftover."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import wakeup

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8584-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_harness_wakeup_33717474657_billing_lock.py"
PRIOR_VERIFY = ROOT / "p/grokbuild-pr8546-verify-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/harness-wakeup.yml"

KEEP = {
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "test_grokbuild_harness_wakeup_33717474657_billing_lock.py": "760a8169",
    "p/grokbuild-pr8546-verify-20260903-01.md": "4e4d8003",
    ".github/workflows/harness-wakeup.yml": "813043ab",
    "wakeup.py": "7988ceb2",
    "test_wakeup_reliability.py": "aca39ab4",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8584Verify(unittest.TestCase):
    def test_keep_8584_leftover_and_peers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 wakeup.py", yml)
        self.assertIn("git add wakeups.json wakeups/fired.json", yml)
        self.assertIn("git push origin HEAD:main", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_cites_8584_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        prior = PRIOR_VERIFY.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8584-verify-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8584@51814ebf019d53c42ec170b4ed626eb0036fc48e",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8584", text)
        self.assertIn("51814ebf019d53c42ec170b4ed626eb0036fc48e", text)
        self.assertIn("e2699ed63748e7be9d1820c4722d09c8eaf5c04f", text)
        self.assertIn("0ddbdaf51fee6870caf1572ff53db1293852b72b", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("f54e1846", text)
        self.assertIn("760a8169", text)
        self.assertIn("4e4d8003", text)
        self.assertIn("813043ab", text)
        self.assertIn("7988ceb2", text)
        self.assertIn("aca39ab4", text)
        self.assertIn("4b053e43", text)
        self.assertIn("Did not remint leftover grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("33717474657", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotIn("woahwhattheheck/commons#8584@", leftover)
        self.assertNotIn("woahwhattheheck/commons#8584@", prior)

    def test_local_bake_still_passes(self) -> None:
        saved = (wakeup.ROOT, wakeup.now, wakeup.ntfy)
        with tempfile.TemporaryDirectory(prefix="wakeup-pr8584-") as tmp:
            os.makedirs(os.path.join(tmp, "wakeups"), exist_ok=True)
            job = {
                "from": "CODEX_LOCAL",
                "id": "codex-wakeup-pr8584-verify",
                "wakeup": "2026-08-22T22:00:00Z",
                "adapter": "Codex/local/GitHub Actions",
            }
            with open(os.path.join(tmp, "wakeups", "CODEX_LOCAL.json"), "w", encoding="utf-8") as handle:
                json.dump(job, handle)
            wakeup.ROOT = tmp
            wakeup.ntfy = lambda _row, _attempt_id: True
            try:
                self.assertEqual(wakeup.main(), 0)
                with open(os.path.join(tmp, "wakeups", "fired.json"), encoding="utf-8") as handle:
                    fired = json.load(handle)
                self.assertIn("codex-wakeup-pr8584-verify", fired.get("ids") or [])
                self.assertEqual(wakeup.main(), 0)
                with open(os.path.join(tmp, "wakeups.json"), encoding="utf-8") as handle:
                    public = json.load(handle)
            finally:
                wakeup.ROOT, wakeup.now, wakeup.ntfy = saved
        self.assertEqual(public.get("due"), [])
        self.assertIn("codex-wakeup-pr8584-verify", public.get("fired") or [])

    def test_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_harness_wakeup_33717474657_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
