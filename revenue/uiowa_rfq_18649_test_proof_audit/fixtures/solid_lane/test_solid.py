"""Ground-truth fixture: the auditor must report NOTHING here.

It includes a helper-indirection case on purpose. A suite that factors its
checks into a helper is not hollow, and flagging it would be the over-fire
that gets a linter switched off within a day.
"""

import unittest

import solid


class TestSolid(unittest.TestCase):
    def _expect_doubled(self, value, expected):
        self.assertEqual(solid.double(value), expected)

    def test_double_returns_twice(self):
        self.assertEqual(solid.double(3), 6)

    def test_a_negative_rate_is_refused(self):
        with self.assertRaises(solid.RuleError):
            solid.validate_rate(-1)

    def test_a_valid_rate_comes_back(self):
        self.assertEqual(solid.validate_rate(5), 5)

    def test_via_a_helper_still_counts(self):
        self._expect_doubled(4, 8)
