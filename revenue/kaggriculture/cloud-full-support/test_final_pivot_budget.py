# SPDX-License-Identifier: Apache-2.0
"""Regression coverage for the exact simplex final-pivot bit-budget boundary."""
from __future__ import annotations

from fractions import Fraction as F
import importlib.util
import json
from pathlib import Path
import random
import unittest

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / 'full_support.py'


def load_runtime(path=RUNTIME):
    spec = importlib.util.spec_from_file_location('triad_final_pivot_runtime', path)
    if spec is None or spec.loader is None:
        raise ValueError('Cannot load supplied full-support runtime')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def number(value):
    if isinstance(value, bool):
        raise ValueError('Boolean is not a receipt')
    return F(str(value)) if isinstance(value, float) else F(value)


def rows_of(deltas):
    return tuple(tuple(number(x) for x in row) for row in deltas)


def old_loop_trace(deltas, *, max_pivots=128, max_bits=16):
    """Execute the former loop ordering and expose its unchecked optimal exit."""
    rows = rows_of(deltas)
    n, m = len(rows), len(rows[0])
    too_big = lambda x: max(x.numerator.bit_length(), x.denominator.bit_length()) > max_bits
    if any(too_big(x) for row in rows for x in row):
        raise ValueError('input exceeds budget')
    shift = max(F(1), F(1) - min(min(row) for row in rows))
    table = [[x + shift for x in row] + [F(int(i == k)) for k in range(n)] + [F(1)]
             for i, row in enumerate(rows)]
    table.append([F(-1)] * m + [F(0)] * (n + 1))
    basis = list(range(m, m + n))
    pivots = 0
    while True:
        entering = next((j for j, cost in enumerate(table[-1][:-1]) if cost < 0), None)
        if entering is None:
            return {'status': 'optimal', 'pivots': pivots,
                    'oversized': any(too_big(x) for row in table for x in row)}
        if pivots >= max_pivots:
            return {'status': 'pivot_limit', 'pivots': pivots,
                    'oversized': any(too_big(x) for row in table for x in row)}
        if any(too_big(x) for row in table for x in row):
            return {'status': 'bit_limit', 'pivots': pivots, 'oversized': True}
        eligible = [i for i in range(n) if table[i][entering] > 0]
        if not eligible:
            raise ArithmeticError('unexpected unbounded shifted game')
        leaving = min(eligible, key=lambda i: (table[i][-1] / table[i][entering], basis[i]))
        pivot = table[leaving][entering]
        table[leaving] = [x / pivot for x in table[leaving]]
        for i in range(n + 1):
            if i != leaving and table[i][entering]:
                factor = table[i][entering]
                table[i] = [a - factor * b for a, b in zip(table[i], table[leaving])]
        basis[leaving] = entering
        pivots += 1


def boundary_cases(runtime, count=9):
    """Find deterministic legal tables where only the old final exit missed the limit."""
    rng = random.Random(20260908)
    found = []
    fingerprints = set()
    for attempt in range(12000):
        alternatives = 3 + attempt % 3
        streams = 3 + (attempt // 3) % 3
        table = [[0] * streams]
        table.extend([[rng.randint(-30000, 30000) for _ in range(streams)]
                      for _ in range(alternatives)])
        fingerprint = json.dumps(table, separators=(',', ':'))
        if fingerprint in fingerprints:
            continue
        trace = old_loop_trace(table, max_bits=16)
        if trace['status'] != 'optimal' or not trace['oversized'] or trace['pivots'] == 0:
            continue
        runtime.clear_table_cache()
        result = runtime.solve_full_table(table, max_bits=16)
        if result['status'] != 'bit_limit':
            continue
        if runtime.verify_certificate(table, result).get('valid') is not True:
            continue
        fingerprints.add(fingerprint)
        found.append((table, trace, result))
        if len(found) == count:
            return found
    raise AssertionError(f'Found only {len(found)} final-pivot boundary tables')


class FinalPivotBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = load_runtime()
        cls.cases = boundary_cases(cls.runtime)
        cls.table, cls.old, cls.limited = cls.cases[0]
        cls.runtime.clear_table_cache()
        cls.unlimited = cls.runtime.solve_full_table(cls.table, max_bits=512)

    def test_01_finds_nine_deterministic_boundaries(self):
        self.assertEqual(len(self.cases), 9)

    def test_02_old_order_exits_optimal_on_oversized_tableau(self):
        self.assertEqual(self.old['status'], 'optimal')
        self.assertTrue(self.old['oversized'])

    def test_03_corrected_order_reports_bit_limit(self):
        self.assertEqual(self.limited['status'], 'bit_limit')

    def test_04_limit_result_is_not_exact(self):
        self.assertIs(self.limited['exact'], False)

    def test_05_limit_result_retains_baseline_weights(self):
        self.assertEqual(self.limited['weights'], ['1'] + ['0'] * (len(self.table) - 1))

    def test_06_limit_result_retains_baseline_support(self):
        self.assertEqual(self.limited['support'], [0])

    def test_07_limit_certificate_is_valid(self):
        self.assertTrue(self.runtime.verify_certificate(self.table, self.limited)['valid'])

    def test_08_limit_lower_bound_is_zero(self):
        self.assertEqual(F(self.limited['value']), 0)

    def test_09_limit_upper_bound_is_not_below_lower(self):
        self.assertGreaterEqual(F(self.limited['upper_bound']), F(self.limited['value']))

    def test_10_limit_gap_matches_bounds(self):
        self.assertEqual(F(self.limited['gap']),
                         F(self.limited['upper_bound']) - F(self.limited['value']))

    def test_11_boundary_requires_at_least_one_pivot(self):
        self.assertGreater(self.limited['pivots'], 0)

    def test_12_declared_bit_budget_is_retained(self):
        self.assertEqual(self.limited['max_bits'], 16)

    def test_13_same_table_hash_across_budgets(self):
        self.assertEqual(self.limited['table_sha256'], self.unlimited['table_sha256'])

    def test_14_larger_budget_completes_same_problem(self):
        self.assertEqual(self.unlimited['status'], 'optimal')
        self.assertTrue(self.unlimited['exact'])
        self.assertTrue(self.runtime.verify_certificate(self.table, self.unlimited)['valid'])

    def test_15_cache_identity_includes_bit_budget(self):
        self.runtime.clear_table_cache()
        self.runtime.solve_full_table(self.table, max_bits=16)
        first = self.runtime.table_cache_info()
        self.runtime.solve_full_table(self.table, max_bits=512)
        second = self.runtime.table_cache_info()
        self.assertEqual(first['misses'], 1)
        self.assertEqual(second['misses'], 2)

    def test_16_cache_hit_returns_detached_result(self):
        self.runtime.clear_table_cache()
        first = self.runtime.solve_full_table(self.table, max_bits=16)
        first['weights'][0] = '0'
        second = self.runtime.solve_full_table(self.table, max_bits=16)
        self.assertEqual(second['weights'][0], '1')
        self.assertEqual(self.runtime.table_cache_info()['hits'], 1)

    def test_17_clear_cache_resets_counters(self):
        self.runtime.solve_full_table(self.table, max_bits=16)
        self.runtime.clear_table_cache()
        info = self.runtime.table_cache_info()
        self.assertEqual((info['hits'], info['misses'], info['currsize']), (0, 0, 0))

    def test_18_exact_pivot_limit_semantics_are_unchanged(self):
        self.runtime.clear_table_cache()
        result = self.runtime.solve_full_table([[0, 0], [1, -1], [-1, 2]],
                                               max_pivots=0, max_bits=512)
        self.assertEqual(result['status'], 'pivot_limit')
        self.assertEqual(result['support'], [0])
        self.assertTrue(self.runtime.verify_certificate([[0, 0], [1, -1], [-1, 2]], result)['valid'])

    def test_19_zero_value_optimum_still_retains_baseline(self):
        self.runtime.clear_table_cache()
        result = self.runtime.solve_full_table([[0], [0]], max_bits=16)
        self.assertEqual(result['status'], 'optimal')
        self.assertEqual(result['weights'], ['1', '0'])
        self.assertEqual(result['support'], [0])

    def test_20_default_budget_corpus_remains_complete_and_valid(self):
        rng = random.Random(424242)
        for case in range(72):
            streams = 2 + case % 5
            plans = 2 + (case // 5) % 5
            table = [[0] * streams]
            table.extend([[rng.randint(-120, 120) for _ in range(streams)]
                          for _ in range(plans - 1)])
            with self.subTest(case=case):
                self.runtime.clear_table_cache()
                result = self.runtime.solve_full_table(table)
                self.assertEqual(result['status'], 'optimal')
                self.assertTrue(self.runtime.verify_certificate(table, result)['valid'])

    def test_21_all_boundary_cases_preserve_contract(self):
        for index, (table, old, result) in enumerate(self.cases):
            with self.subTest(case=index):
                self.assertEqual(old['status'], 'optimal')
                self.assertTrue(old['oversized'])
                self.assertEqual(result['status'], 'bit_limit')
                self.assertEqual(result['support'], [0])
                self.assertTrue(self.runtime.verify_certificate(table, result)['valid'])


if __name__ == '__main__':
    unittest.main()
