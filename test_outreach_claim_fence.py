"""Stable unittest entrypoint for the outreach claim fence suite."""

import unittest

from outreach_claim_fence_protocol_tests import ClaimFenceProtocolTests
from outreach_claim_fence_lifecycle_tests import ClaimFenceLifecycleTests
from outreach_claim_fence_validation_tests import ClaimFenceValidationTests


def load_tests(loader, _standard_tests, _pattern):
    suite = unittest.TestSuite()
    for case in (ClaimFenceProtocolTests, ClaimFenceLifecycleTests, ClaimFenceValidationTests):
        suite.addTests(loader.loadTestsFromTestCase(case))
    return suite


if __name__ == "__main__":
    unittest.main(verbosity=2)
