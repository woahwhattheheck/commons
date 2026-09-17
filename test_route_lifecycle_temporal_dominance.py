from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

# Intentionally re-exported: Commons' retained battery discovers root test files,
# so this class makes the complete nested product suite execute in the normal lane.
from tools.outbound_send_guard.test_route_lifecycle import RouteLifecycleTests

ROOT = Path(__file__).resolve().parent
NESTED_MODULE = "tools.outbound_send_guard.test_route_lifecycle"
EXPECTED_NESTED_TESTS = 19


class RouteLifecycleOptimizedProof(unittest.TestCase):
    def test_complete_nested_suite_runs_under_optimized_python(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-O", "-m", "unittest", "-v", NESTED_MODULE],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn(f"Ran {EXPECTED_NESTED_TESTS} tests", completed.stdout)
        self.assertRegex(completed.stdout, r"(?:^|\n)OK(?:\n|$)")


if __name__ == "__main__":
    unittest.main()
