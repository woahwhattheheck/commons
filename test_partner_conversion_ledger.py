"""Root CI bridge for the Partner Conversion Ledger hostile suites.

The retained Commons tests workflow is intentionally path-filtered to root
``test_*.py`` plus core engine surfaces. Keep product assertions in the package;
this file only makes those suites reachable without adding another workflow.
"""
from revenue.partner_conversion_ledger.test_ledger_core import LedgerCoreTests
from revenue.partner_conversion_ledger.test_ledger_runtime import LedgerRuntimeTests

# Keep imported TestCase classes visible to unittest discovery.
__all__ = ["LedgerCoreTests", "LedgerRuntimeTests"]

if __name__ == "__main__":
    import unittest
    unittest.main()
