"""Expose the complete ReuseLedger workflow suite to root discovery."""
from pathlib import Path
import subprocess
import sys
import unittest


class ReuseLedgerWorkflowDiscovery(unittest.TestCase):
    def test_workflow_suite(self):
        component = Path(__file__).resolve().parent / "competitions" / "nci-ods-impact-prize-2026"
        flags = [] if __debug__ else ["-O"]
        result = subprocess.run(
            [sys.executable, *flags, "-m", "unittest", "-v", "test_reuse_workflow"],
            cwd=component, text=True, capture_output=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
