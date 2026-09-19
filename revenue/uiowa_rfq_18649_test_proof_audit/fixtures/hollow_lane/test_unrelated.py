"""Ground-truth fixture: real assertions, about nothing in this lane."""

import unittest


class TestArithmetic(unittest.TestCase):
    def test_addition(self):
        total = 2 + 3
        self.assertEqual(total, 5)
