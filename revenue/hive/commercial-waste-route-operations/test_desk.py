#!/usr/bin/env python3

import unittest

from test_support import MANIFEST
from test_desk_core import CoreDeskTests
from test_desk_billing import BillingDeskTests


if __name__ == "__main__":
    unittest.main(verbosity=2)
