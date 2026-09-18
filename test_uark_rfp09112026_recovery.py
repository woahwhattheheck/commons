#!/usr/bin/env python3
"""Enroll the canonical UArk recovery suites in Commons' retained root CI battery.

The dedicated UArk workflow was intentionally not restored: workflow-surface
budget is a repository-level invariant. This root bridge is path-triggered by
`.github/workflows/tests.yml` and executes the exact nested recovery suites in
both normal and optimized interpreters.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUITES = (
    "tests/test_uark_rfp09112026_cmmc.py",
    "tests/test_uark_rfp09112026_current_authority.py",
    "tests/test_uark_rfp09112026_current_entry.py",
)


class UarkRecoveryRootBridge(unittest.TestCase):
    def test_uark_recovery_suites_normal_and_optimized(self) -> None:
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                command = [sys.executable]
                if optimized:
                    command.append("-O")
                command.extend(["-m", "unittest", "-v", *SUITES])
                done = subprocess.run(
                    command,
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=180,
                )
                detail = (done.stdout + "\n" + done.stderr)[-12000:]
                self.assertEqual(done.returncode, 0, detail)


if __name__ == "__main__":
    unittest.main()
