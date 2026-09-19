"""Expose the scoped mortgage reconciliation acceptance suite to root discovery."""
from pathlib import Path
import subprocess
import sys
import unittest


class MortgageCaseReconciliationSuite(unittest.TestCase):
    def test_component_suite(self):
        component = (Path(__file__).resolve().parent / "revenue" /
                     "lloyds_launch_2026_mortgage_case_reconcile")
        optimization = ["-" + "O" * sys.flags.optimize] if sys.flags.optimize else []
        result = subprocess.run(
            [sys.executable, "-B", *optimization, "-m", "unittest", "discover",
             "-s", ".", "-p", "test_mortgage_case_reconcile.py", "-v"],
            cwd=component, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
