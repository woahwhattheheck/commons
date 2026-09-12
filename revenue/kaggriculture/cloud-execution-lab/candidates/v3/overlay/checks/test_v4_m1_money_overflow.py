# SPDX-License-Identifier: Apache-2.0
"""Regression: hostile numeric money must fail closed instead of raising."""
from __future__ import annotations

import math
import unittest

import r04_m1_wheat_trade as m1


class M1MoneyOverflowTests(unittest.TestCase):
    def test_huge_json_integer_is_not_valid_money_and_does_not_raise(self):
        huge = 10 ** 1000
        with self.assertRaises(OverflowError):
            math.isfinite(huge)
        self.assertIs(m1._plain_nonnegative_money(huge), False)

    def test_finite_nonnegative_money_still_accepts_normal_engine_values(self):
        for value in (0, 1, 1000, 1000.0, 1234.5):
            with self.subTest(value=value):
                self.assertIs(m1._plain_nonnegative_money(value), True)

    def test_bool_negative_nan_and_inf_are_rejected(self):
        for value in (True, False, -1, -0.5, float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value):
                self.assertIs(m1._plain_nonnegative_money(value), False)


if __name__ == "__main__":
    unittest.main()
