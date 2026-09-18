"""Hosted proof hook for the UNC AP/PeopleSoft compiler.\n\nA branch-head change to this file intentionally triggers the standard tests workflow.\n"""

from pathlib import Path
import subprocess
import sys
import unittest

PACKAGE = Path(__file__).parent / "revenue" / "opportunities" / "unc_ap_ai_peoplesoft"

class HostedProof(unittest.TestCase):
    def run_suite(self, optimized):
        argv = [sys.executable]
        if optimized:
            argv.append("-O")
        argv += ["-m", "unittest", "-v", "test_unc_ap_ai.py"]
        result = subprocess.run(
            argv, cwd=PACKAGE, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120,
        )
        if result.returncode:
            self.fail(result.stdout)

    def test_normal(self):
        self.run_suite(False)

    def test_optimized(self):
        self.run_suite(True)

if __name__ == "__main__":
    unittest.main()
