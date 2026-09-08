# SPDX-License-Identifier: Apache-2.0
"""Regression for arithmetic exhaustion produced by the final simplex pivot."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import importlib.util
import random
import unittest

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location(
        'final_pivot_budget_runtime', HERE / 'full_support.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bit_length(value: F) -> int:
    return max(value.numerator.bit_length(), value.denominator.bit_length())


def _is_final_pivot_overflow(deltas, max_bits=16):
    """Independent tableau probe; never calls the production solver."""
    rows = tuple(tuple(F(value) for value in row) for row in deltas)
    n, m = len(rows), len(rows[0])
    too_big = lambda value: _bit_length(value) > max_bits
    if any(too_big(value) for row in rows for value in row):
        return None
    shift = max(F(1), F(1) - min(min(row) for row in rows))
    table = [[value + shift for value in row]
             + [F(int(index == basis_row)) for basis_row in range(n)] + [F(1)]
             for index, row in enumerate(rows)]
    table.append([F(-1)] * m + [F(0)] * (n + 1))
    basis = list(range(m, m + n))
    pivots = 0
    while True:
        entering = next((column for column, cost in enumerate(table[-1][:-1])
                         if cost < 0), None)
        if entering is None or any(too_big(value) for row in table for value in row):
            return None
        eligible = [row for row in range(n) if table[row][entering] > 0]
        if not eligible:
            return None
        leaving = min(eligible,
                      key=lambda row: (table[row][-1] / table[row][entering], basis[row]))
        pivot = table[leaving][entering]
        table[leaving] = [value / pivot for value in table[leaving]]
        for row in range(n + 1):
            if row != leaving and table[row][entering]:
                factor = table[row][entering]
                table[row] = [left - factor * right
                              for left, right in zip(table[row], table[leaving])]
        basis[leaving] = entering
        pivots += 1
        overflow = any(too_big(value) for row in table for value in row)
        next_entering = next((column for column, cost in enumerate(table[-1][:-1])
                              if cost < 0), None)
        if overflow and next_entering is None:
            return {'pivots': pivots,
                    'max_tableau_bits': max(_bit_length(value)
                                            for row in table for value in row)}
        if overflow:
            return None


def _find_discriminator():
    """Find one stable final-pivot case from a bounded deterministic corpus."""
    rng = random.Random(20260908)
    for attempt in range(1, 100001):
        n, m = rng.choice(((4, 3), (5, 4), (6, 5)))
        deltas = [[0] * m]
        for _ in range(n - 1):
            row = [rng.randint(-191, 191) for _ in range(m)]
            if not any(row):
                row[0] = 1
            deltas.append(row)
        probe = _is_final_pivot_overflow(deltas)
        if probe is not None:
            return deltas, probe, attempt
    raise AssertionError('bounded corpus contains no final-pivot discriminator')


class FinalPivotBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = _load()
        cls.deltas, cls.probe, cls.attempt = _find_discriminator()
        cls.runtime.clear_table_cache()
        cls.limited = cls.runtime.solve_full_table(cls.deltas, max_bits=16)
        cls.unlimited = cls.runtime.solve_full_table(cls.deltas, max_bits=512)

    def test_probe_reaches_final_pivot(self):
        self.assertGreater(self.probe['pivots'], 0)

    def test_probe_exceeds_budget(self):
        self.assertGreater(self.probe['max_tableau_bits'], 16)

    def test_discriminator_is_bounded(self):
        self.assertLessEqual(self.attempt, 100000)

    def test_limited_status(self):
        self.assertEqual(self.limited['status'], 'bit_limit')

    def test_limited_not_exact(self):
        self.assertIs(self.limited['exact'], False)

    def test_limited_keeps_baseline(self):
        self.assertEqual(self.limited['weights'], ['1'] + ['0'] * (len(self.deltas) - 1))
        self.assertEqual(self.limited['support'], [0])

    def test_limited_certificate_is_valid(self):
        self.assertTrue(self.limited['certificate_valid'])
        self.assertTrue(self.runtime.verify_certificate(self.deltas, self.limited)['valid'])

    def test_limited_bounds_are_ordered(self):
        self.assertLessEqual(F(self.limited['value']), F(self.limited['upper_bound']))
        self.assertEqual(F(self.limited['gap']),
                         F(self.limited['upper_bound']) - F(self.limited['value']))

    def test_limited_records_completed_pivots(self):
        self.assertEqual(self.limited['pivots'], self.probe['pivots'])

    def test_default_budget_completes_same_table(self):
        self.assertEqual(self.unlimited['status'], 'optimal')
        self.assertTrue(self.unlimited['exact'])

    def test_default_certificate_is_valid(self):
        self.assertTrue(self.unlimited['certificate_valid'])
        self.assertTrue(self.runtime.verify_certificate(self.deltas, self.unlimited)['valid'])

    def test_budget_is_part_of_cache_identity(self):
        info = self.runtime.table_cache_info()
        self.assertGreaterEqual(info['currsize'], 2)

    def test_cache_returns_detached_result(self):
        first = self.runtime.solve_full_table(self.deltas, max_bits=16)
        first['weights'][0] = '0'
        again = self.runtime.solve_full_table(self.deltas, max_bits=16)
        self.assertEqual(again['weights'][0], '1')

    def test_cache_clear_is_public(self):
        self.runtime.clear_table_cache()
        self.assertEqual(self.runtime.table_cache_info()['currsize'], 0)
        self.runtime.solve_full_table(self.deltas, max_bits=16)

    def test_input_is_not_mutated(self):
        original = deepcopy(self.deltas)
        self.runtime.solve_full_table(self.deltas, max_bits=16)
        self.assertEqual(self.deltas, original)

    def test_ordered_table_digest_is_retained(self):
        reversed_rows = [self.deltas[0]] + list(reversed(self.deltas[1:]))
        self.assertNotEqual(self.runtime.solve_full_table(
            reversed_rows, max_bits=16)['table_sha256'], self.limited['table_sha256'])

    def test_pivot_limit_contract_is_unchanged(self):
        result = self.runtime.solve_full_table(self.deltas, max_pivots=0, max_bits=512)
        self.assertEqual(result['status'], 'pivot_limit')
        self.assertEqual(result['support'], [0])
        self.assertTrue(self.runtime.verify_certificate(self.deltas, result)['valid'])

    def test_zero_table_keeps_baseline(self):
        result = self.runtime.solve_full_table([[0, 0], [0, 0]])
        self.assertEqual(result['status'], 'optimal')
        self.assertEqual(result['weights'], ['1', '0'])
        self.assertEqual(result['value'], '0')

    def test_positive_small_table_remains_optimal(self):
        result = self.runtime.solve_full_table([[0, 0], [1, 1]])
        self.assertEqual(result['status'], 'optimal')
        self.assertEqual(result['weights'], ['0', '1'])
        self.assertEqual(result['value'], '1')

    def test_boolean_bit_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.solve_full_table([[0]], max_bits=True)

    def test_boolean_pivot_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.solve_full_table([[0]], max_pivots=True)


if __name__ == '__main__':
    unittest.main()
