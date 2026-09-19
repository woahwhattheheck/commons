"""Ground-truth fixture: collected by a discovery runner, contains no tests.

This is the shape that reports `Ran 0 tests ... OK`.
"""

import unittest


class Helper(unittest.TestCase):
    def helper_only(self):
        return 1
