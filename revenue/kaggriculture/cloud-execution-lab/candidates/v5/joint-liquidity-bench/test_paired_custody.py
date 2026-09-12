# SPDX-License-Identifier: Apache-2.0
"""Focused custody regressions for the V5 joint-liquidity launcher."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "paired.py"
SPEC = importlib.util.spec_from_file_location("_v5_joint_liquidity_paired", SOURCE)
paired = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(paired)


class JointLiquidityCustodyTests(unittest.TestCase):
    def test_only_published_overlay_sha_is_accepted(self):
        self.assertEqual(
            paired.published_overlay_sha256(paired.OVERLAY_SHA256),
            paired.OVERLAY_SHA256,
        )
        for value in (
            "0" * 64,
            paired.OVERLAY_SHA256.upper(),
            paired.OVERLAY_SHA256[:-1],
            None,
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "must match published"):
                    paired.published_overlay_sha256(value)

    def test_forged_self_hash_fails_before_any_output_for_both_candidate_paths(self):
        forged = "0" * 64
        for mode in ("--overlay", "--candidate"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(
                prefix="joint-liquidity-custody-"
            ) as raw:
                root = Path(raw)
                output = root / "evidence"
                argv = [
                    "paired.py",
                    "--kg-root", str(root / "unused-kg"),
                    "--engine-dir", str(root / "unused-engine"),
                    "--baseline", str(root / "unused-v4.tar.gz"),
                    mode, str(root / "attacker-controlled-input"),
                    "--overlay-sha256", forged,
                    "--output", str(output),
                ]
                with patch.object(sys, "argv", argv):
                    with self.assertRaisesRegex(ValueError, "must match published"):
                        paired.main()
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
