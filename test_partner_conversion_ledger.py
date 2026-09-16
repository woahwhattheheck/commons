"""Root CI bridge for the Partner Conversion Ledger hostile suites.

The retained Commons tests workflow is intentionally path-filtered to root
``test_*.py`` plus core engine surfaces. Keep product assertions in the package;
this file only makes those suites reachable without adding another workflow.
"""
from __future__ import annotations

import subprocess
import sys
import unittest

from revenue.partner_conversion_ledger.test_ledger_core import LedgerCoreTests
from revenue.partner_conversion_ledger.test_ledger_runtime import LedgerRuntimeTests

# Keep imported TestCase classes visible to unittest discovery.
__all__ = ["LedgerCoreTests", "LedgerRuntimeTests", "PartnerConversionOptimizedSuiteTests"]


class PartnerConversionOptimizedSuiteTests(unittest.TestCase):
    def test_package_hostiles_also_pass_under_python_O(self):
        result = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-v",
                "revenue.partner_conversion_ledger.test_ledger_core",
                "revenue.partner_conversion_ledger.test_ledger_runtime",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
