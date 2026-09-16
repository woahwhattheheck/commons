#!/usr/bin/env python3
"""LATCH canary: battery must not dirty tracked ground/MANUAL.md.

Measured fail: GitHub Actions tests run 35142797410 / job 104951596877
SHA 6d2b80273b80026f1aaaae6addf1015346337461
FAIL test_zzzzzzzz_tracked_checkout_clean.js
message: tracked-checkout-clean: test battery modified tracked files
dirty path: ground/MANUAL.md

Writer: test_grokbuild_tests_battery_34395174679_keep_lift.py called
manual_build.main() against live OUT. TYPE #14983 redirected that rebuild
to a tempfile on main. This file keeps that contract so a later caller
cannot silently rewrite the living manual during the battery.

Do not remint type-manual-rebuild-larger-keep-20260916-01.
Cite Latch Pad KEEP. Tip KEEP. Hands off #8802.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import manual_build

ROOT = Path(__file__).resolve().parent
KEEP_LIFT = ROOT / "test_grokbuild_tests_battery_34395174679_keep_lift.py"
REBAKE = ROOT / "test_manual_tools_rebake.py"
MANUAL = ROOT / "ground" / "MANUAL.md"
CI_RUN = "35142797410"
WRITER = "test_grokbuild_tests_battery_34395174679_keep_lift.py"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _test_files() -> list[Path]:
    files = [p for p in ROOT.glob("test_*.py") if p.is_file() and not p.is_symlink()]
    infra = ROOT / "infra"
    if infra.is_dir() and not infra.is_symlink():
        files.extend(infra.rglob("test_*.py"))
    return sorted(p for p in files if p.is_file() and not p.is_symlink())


class LatchManualRebuildBatteryCleanTests(unittest.TestCase):
    def test_keep_lift_source_rebuilds_to_tempfile_not_live_out(self) -> None:
        text = KEEP_LIFT.read_text(encoding="utf-8")
        self.assertIn("TemporaryDirectory", text)
        self.assertIn('patch.object(manual_build, "OUT"', text)
        self.assertIn("manual_build.main(", text)
        self.assertIn(CI_RUN, text)

    def test_every_battery_caller_of_manual_build_main_patches_out(self) -> None:
        offenders = []
        for path in _test_files():
            text = path.read_text(encoding="utf-8")
            if "manual_build.main(" not in text:
                continue
            if 'patch.object(manual_build, "OUT"' in text:
                continue
            if "patch.object(manual_build, 'OUT'" in text:
                continue
            offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(
            offenders,
            [],
            "test callers of manual_build.main() must patch OUT away from live ground/MANUAL.md",
        )

    def test_rebake_also_patches_out(self) -> None:
        text = REBAKE.read_text(encoding="utf-8")
        self.assertIn("manual_build.main(", text)
        self.assertIn('patch.object(manual_build, "OUT"', text)

    def test_tempfile_rebuild_leaves_tracked_manual_clean(self) -> None:
        before = MANUAL.read_text(encoding="utf-8")
        before_blob = _git("hash-object", "ground/MANUAL.md")
        self.assertEqual(before_blob.returncode, 0, before_blob.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "MANUAL.md"
            with patch.object(manual_build, "OUT", str(out)):
                rc = manual_build.main()
            rebuilt = out.read_text(encoding="utf-8")
        self.assertEqual(rc, 0)
        self.assertIn("Build ledger: [builds.html](../builds.html)", rebuilt)
        self.assertIn("Larger fixed engagements", rebuilt)
        self.assertEqual(before, MANUAL.read_text(encoding="utf-8"))
        after_blob = _git("hash-object", "ground/MANUAL.md")
        self.assertEqual(after_blob.stdout, before_blob.stdout)
        dirty = _git("diff", "--quiet", "--no-ext-diff", "--", "ground/MANUAL.md")
        self.assertEqual(dirty.returncode, 0, dirty.stdout + dirty.stderr)

    def test_keep_lift_file_leaves_manual_tracked_clean(self) -> None:
        keep = subprocess.run(
            ["python3", "./" + KEEP_LIFT.name],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(keep.returncode, 0, keep.stdout + keep.stderr)
        dirty = _git("diff", "--name-only", "--no-ext-diff", "--", "ground/MANUAL.md")
        self.assertEqual(dirty.returncode, 0, dirty.stderr)
        self.assertEqual(dirty.stdout.strip(), "")

    def test_receipt_names_writer_and_does_not_remint_type(self) -> None:
        receipt = ROOT / "p/latch-manual-rebuild-battery-clean-20260916-01.md"
        self.assertTrue(receipt.is_file(), "missing LATCH receipt")
        text = receipt.read_text(encoding="utf-8")
        self.assertIn("CLAIM LATCH", text)
        self.assertIn(WRITER, text)
        self.assertIn(CI_RUN, text)
        self.assertIn("ground/MANUAL.md", text)
        self.assertIn("type-manual-rebuild-larger-keep-20260916-01", text)
        self.assertNotIn("type-password", text)
        self.assertNotIn("Authorization", text)
        self.assertNotIn("buy.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
