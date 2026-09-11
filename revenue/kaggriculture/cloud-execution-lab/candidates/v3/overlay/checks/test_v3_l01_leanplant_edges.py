# SPDX-License-Identifier: Apache-2.0
"""Regression checks for L01 LEANPLANT boundary counts."""
from __future__ import annotations

from collections import Counter
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import l01_mechanics as l01  # noqa: E402


def synthetic_route(wheat_count):
    """One WHEAT farmer plus one unrelated CARROT hand per row."""
    return [
        {
            'farmer': ['PLANT', 'WHEAT'],
            'hands': [['PLANT', 'CARROT']],
            'market': [],
        }
        for _ in range(wheat_count)
    ]


def apply_leanplant(route):
    activations = Counter()
    l01.patch_routes({'synthetic': route}, {'LEANPLANT': True}, activations, [])
    return activations


class LeanplantBoundaryTests(unittest.TestCase):
    def test_at_or_below_keep_count_is_identity(self):
        for wheat_count in (0, 1, 71, 72):
            with self.subTest(wheat_count=wheat_count):
                route = synthetic_route(wheat_count)
                before = copy.deepcopy(route)
                activations = apply_leanplant(route)
                self.assertEqual(route, before)
                self.assertEqual(activations, Counter())

    def test_one_over_limit_converts_only_last_wheat(self):
        route = synthetic_route(73)
        activations = apply_leanplant(route)
        self.assertEqual(l01.plant_counts(route)['WHEAT'], 72)
        self.assertEqual(l01.plant_counts(route)['CARROT'], 73)
        self.assertEqual(route[71]['farmer'], ['PLANT', 'WHEAT'])
        self.assertEqual(route[72]['farmer'], ['PASS'])
        self.assertEqual(activations, Counter({'LEANPLANT': 1}))

    def test_large_route_truncates_tail_and_is_idempotent(self):
        route = synthetic_route(100)
        activations = apply_leanplant(route)
        self.assertEqual(l01.plant_counts(route)['WHEAT'], 72)
        self.assertEqual(l01.plant_counts(route)['CARROT'], 100)
        self.assertTrue(all(row['farmer'] == ['PLANT', 'WHEAT'] for row in route[:72]))
        self.assertTrue(all(row['farmer'] == ['PASS'] for row in route[72:]))
        self.assertEqual(activations, Counter({'LEANPLANT': 28}))

        before_second = copy.deepcopy(route)
        second_activations = apply_leanplant(route)
        self.assertEqual(route, before_second)
        self.assertEqual(second_activations, Counter())


if __name__ == '__main__':
    unittest.main(verbosity=2)
