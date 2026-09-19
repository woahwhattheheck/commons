"""Expose the delivery-bundle regression suite to the existing root CI battery."""
import unittest

from revenue.uiowa_rfq_18649_delivery_bundle.test_bundle import BundleTests, CommandTests
from revenue.uiowa_rfq_18649_delivery_bundle.test_unicode import UnicodeTests

if __name__ == "__main__":
    unittest.main()
