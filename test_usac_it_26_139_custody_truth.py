"""Retained-battery bridge for the USAC IT-26-139 custody-truth gate.

The opportunity keeps its focused suite beside the source package, while Commons' retained
`tests` workflow is triggered by and discovers root `test_*.py`. Re-export the exact nested
unittest class for ordinary discovery and separately execute the same suite under `python -O`
so recovered-hash/custody and fail-closed authority predecessors are exercised in both modes.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from opportunities.usac_it_26_139_ai_consulting.test_qualify import USACBridgeGateTests


ROOT = Path(__file__).resolve().parent
NESTED = "opportunities.usac_it_26_139_ai_consulting.test_qualify"


class OptimizedModeTests(unittest.TestCase):
    def test_usac_custody_truth_suite_under_python_optimized(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-O", "-m", "unittest", NESTED],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=90,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)


if __name__ == "__main__":
    unittest.main()
