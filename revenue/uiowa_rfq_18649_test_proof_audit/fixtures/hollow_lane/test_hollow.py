"""Ground-truth fixture. Three of these four methods prove little or nothing,
and they are deliberately different kinds of nothing."""

import unittest

import hollow


class TestHollow(unittest.TestCase):
    def test_double_returns_twice(self):
        self.assertEqual(hollow.double(3), 6)

    def test_rate_is_accepted(self):
        # No assertion, but it does call the code -- a smoke test. It would
        # fail if validate_rate raised, so it is weak, not vacuous.
        hollow.validate_rate(5)

    def test_expected_value(self):
        # No assertion and no call. Nothing this does can fail.
        expected = 6

    def test_always_true(self):
        self.assertTrue(True)
