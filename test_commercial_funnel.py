"""Root CI bridge for the commercial-funnel authority hostile suites."""
from __future__ import annotations

import unittest

from revenue.commercial_funnel import (
    test_casefold_identity,
    test_cli,
    test_ledger,
    test_review_regressions,
)

_MODULES = (
    test_ledger,
    test_cli,
    test_review_regressions,
    test_casefold_identity,
)


def load_tests(
    loader: unittest.TestLoader,
    tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for module in _MODULES:
        suite.addTests(loader.loadTestsFromModule(module))
    return suite


if __name__ == "__main__":
    unittest.main()
