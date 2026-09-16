#!/usr/bin/env python3
"""Regression: living MANUAL.md must not pin a frozen git blob prefix.

Delayed tests/battery run 35143510019 on already-merged PR #14877
(head 9a91148fbc63d25ea334f16b906a421448461faa) failed
test_zzzzzzzz_tracked_checkout_clean.js because keep_lift wrote live
ground/MANUAL.md. TYPE #14983 / LATCH #14985 redirected that rebuild
to a tempfile. Unique leftover on current main: keep_lift still pinned
git blob prefix 60235e5d, which fails after ingest rebakes Open jobs.

Do not remint type-manual-rebuild-larger-keep-20260916-01 or
latch-manual-rebuild-battery-clean-20260916-01. Hands off #8802.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEEP_LIFT = ROOT / "test_grokbuild_tests_battery_34395174679_keep_lift.py"
RECEIPT = ROOT / "p/grok-repair-tests-35143510019-manual-blob-pin-20260916-01.md"
MANUAL = ROOT / "ground" / "MANUAL.md"
CI_RUN = "35143510019"
FAILED_SHA = "9a91148fbc63d25ea334f16b906a421448461faa"
FROZEN_PREFIX = "60235e5d"
POINTER = "Build ledger: [builds.html](../builds.html)"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class GrokRepairTests35143510019ManualBlobPin(unittest.TestCase):
    def test_keep_lift_does_not_pin_living_manual_blob_prefix(self) -> None:
        text = KEEP_LIFT.read_text(encoding="utf-8")
        self.assertNotIn(f'startswith("{FROZEN_PREFIX}")', text)
        self.assertIn("git_blob(\"ground/MANUAL.md\").startswith(\"79a93583\")", text)
        self.assertIn("self.assertIn(POINTER, manual)", text)
        self.assertIn("builds.html", text)
        self.assertIn("wire.html", text)
        self.assertIn('patch.object(manual_build, "OUT"', text)
        self.assertIn(CI_RUN, text)

    def test_live_manual_keeps_builds_pointer_without_frozen_blob(self) -> None:
        manual = MANUAL.read_text(encoding="utf-8")
        self.assertIn(POINTER, manual)
        blob = _git("hash-object", "ground/MANUAL.md")
        self.assertEqual(blob.returncode, 0, blob.stderr)
        self.assertFalse(blob.stdout.strip().startswith(FROZEN_PREFIX))
        self.assertFalse(blob.stdout.strip().startswith("79a93583"))

    def test_keep_lift_module_passes_and_leaves_tracked_manual_clean(self) -> None:
        before = _git("hash-object", "ground/MANUAL.md")
        self.assertEqual(before.returncode, 0, before.stderr)
        keep = subprocess.run(
            ["python3", "./" + KEEP_LIFT.name],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(keep.returncode, 0, keep.stdout + keep.stderr)
        after = _git("hash-object", "ground/MANUAL.md")
        self.assertEqual(after.stdout, before.stdout)
        dirty = _git("diff", "--name-only", "--no-ext-diff", "--", "ground/MANUAL.md")
        self.assertEqual(dirty.returncode, 0, dirty.stderr)
        self.assertEqual(dirty.stdout.strip(), "")

    def test_receipt_names_run_and_does_not_remint_type_or_latch(self) -> None:
        self.assertTrue(RECEIPT.is_file(), "missing repair receipt")
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn(CI_RUN, text)
        self.assertIn(FAILED_SHA, text)
        self.assertIn("test_zzzzzzzz_tracked_checkout_clean.js", text)
        self.assertIn("ground/MANUAL.md", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:9a91148fbc63d25ea334f16b906a421448461faa:the whole battery, one failure fails the run",
            text,
        )
        self.assertIn("type-manual-rebuild-larger-keep-20260916-01", text)
        self.assertIn("latch-manual-rebuild-battery-clean-20260916-01", text)
        self.assertNotIn("type-password", text)
        self.assertNotIn("Authorization", text)
        self.assertNotIn("buy.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
