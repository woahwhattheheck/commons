"""Root-battery bridge for outbound-send-forensics hostile suites.

The package keeps its tests beside the production module; Commons' consolidated
battery discovers root test_*.py files, so this bridge enrolls both nested suites
without adding another active workflow.
"""

import unittest

from revenue.outbound_send_forensics import test_audit, test_authority_root


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(test_audit))
    suite.addTests(loader.loadTestsFromModule(test_authority_root))
    return suite


if __name__ == "__main__":
    unittest.main()
