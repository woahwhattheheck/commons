# SPDX-License-Identifier: Apache-2.0
"""Regression tests for L01 LEANPLANT zero-slice preservation.

The predecessor used ``sites[-extra:]`` even when ``extra == 0``. In Python,
``-0 == 0``, so routes already at or below the 72-WHEAT cap were rewritten
entirely to PASS. These tests bind the intended threshold semantics directly.
"""
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


def wheat_route(count):
    return [
        {'farmer': ['PLANT', 'WHEAT'], 'hands': [], 'market': []}
        for _ in range(count)
    ]


def leanplant_flags():
    return {key: key == 'LEANPLANT' for key in l01.FLAG_KEYS}


class LeanplantZeroSliceTests(unittest.TestCase):
    def patch(self, routes):
        activations = Counter()
        reasons = []
        l01.patch_routes(routes, leanplant_flags(), activations, reasons)
        return activations, reasons

    def test_below_cap_is_exact_identity(self):
        routes = {'short': wheat_route(7)}
        before = copy.deepcopy(routes)
        activations, reasons = self.patch(routes)
        self.assertEqual(routes, before)
        self.assertEqual(activations, Counter())
        self.assertEqual(reasons, [])

    def test_exact_cap_is_exact_identity(self):
        routes = {'cap': wheat_route(l01.KEEP_WHEAT_PLANTS)}
        before = copy.deepcopy(routes)
        activations, _ = self.patch(routes)
        self.assertEqual(routes, before)
        self.assertEqual(activations, Counter())

    def test_above_cap_trims_only_tail(self):
        total = l01.KEEP_WHEAT_PLANTS + 3
        routes = {'long': wheat_route(total)}
        activations, _ = self.patch(routes)
        route = routes['long']
        self.assertTrue(all(row['farmer'] == ['PLANT', 'WHEAT']
                            for row in route[:l01.KEEP_WHEAT_PLANTS]))
        self.assertTrue(all(row['farmer'] == ['PASS']
                            for row in route[l01.KEEP_WHEAT_PLANTS:]))
        self.assertEqual(l01.plant_counts(route)['WHEAT'], l01.KEEP_WHEAT_PLANTS)
        self.assertEqual(activations['LEANPLANT'], 3)

    def test_short_route_survives_beside_long_route_and_repeat(self):
        routes = {
            'long': wheat_route(l01.KEEP_WHEAT_PLANTS + 3),
            'short': wheat_route(4),
        }
        activations, _ = self.patch(routes)
        after_first = copy.deepcopy(routes)
        self.assertEqual(l01.plant_counts(routes['long'])['WHEAT'], l01.KEEP_WHEAT_PLANTS)
        self.assertEqual(l01.plant_counts(routes['short'])['WHEAT'], 4)
        self.assertEqual(activations['LEANPLANT'], 3)

        second_activations, _ = self.patch(routes)
        self.assertEqual(routes, after_first)
        self.assertEqual(second_activations, Counter())


if __name__ == '__main__':
    unittest.main(verbosity=2)
