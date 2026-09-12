# SPDX-License-Identifier: Apache-2.0
import unittest

import p01_productive_expansion_gate as gate


def fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def fake_day_factory(plan_kind='low'):
    low = {18:11,19:10,20:11,21:11,22:10,23:10,24:10,25:10,26:10,27:10,28:11,29:11}
    high = {18:12,19:11,20:12,21:11,22:11,23:11,24:11,25:11,26:11,27:10,28:11,29:11}
    table = low if plan_kind == 'low' else high
    def native_day(native, day):
        return [{'hands': [['PASS']] * table[day]}]
    return native_day


def obs(price=140, inventory=10000, rival_tiles=None):
    own = {'tiles': [[None]]}
    rival = {'tiles': [rival_tiles or [None]]}
    return {
        'player': 0,
        'step': 432,
        'farms': [own, rival],
        'market': {'inventory': {'TOMATO': inventory}, 'prices': {'TOMATO': price}},
    }


class ProductiveExpansionGate(unittest.TestCase):
    def test_route_labor_cost_matches_exact_r04_shapes(self):
        self.assertEqual(gate.route_labor_cost(object(), fake_day_factory('low'), fib), 3694)
        self.assertEqual(gate.route_labor_cost(object(), fake_day_factory('high'), fib), 4668)

    def test_visible_rival_supply_counts_held_and_remaining_fertilized_ceiling(self):
        tile = {'crop':'TOMATO', 'planted_day':12, 'yield_units':3}
        # Production dates 20..23 are all still ahead at day18: 3 held + 4*2 future.
        self.assertEqual(gate.rival_tomato_supply_bound(obs(rival_tiles=[tile])), 11)

    def test_negative_payback_rejects_original_seventy_dollar_entry(self):
        market_price = lambda item, inv: 70
        record = gate.evaluate(obs(price=70), object(), fake_day_factory('low'), fib, market_price)
        self.assertFalse(record['decision'])
        self.assertEqual(record['total_cost'], 8894)
        self.assertEqual(record['projected_gross'], 5600)

    def test_high_quote_clean_field_can_admit(self):
        market_price = lambda item, inv: 140
        record = gate.evaluate(obs(price=140), object(), fake_day_factory('low'), fib, market_price)
        self.assertTrue(record['decision'])
        self.assertGreaterEqual(record['projected_gross'], record['total_cost'])

    def test_visible_rival_supply_can_flip_borderline_case(self):
        # A simple descending curve makes the supply adjustment observable and deterministic.
        curve = lambda item, inv: max(1, 130 - max(0, inv - 10000))
        clean = gate.evaluate(obs(price=130), object(), fake_day_factory('low'), fib, curve)
        rival = {'crop':'TOMATO', 'planted_day':12, 'yield_units':3}
        crowded = gate.evaluate(obs(price=130, rival_tiles=[rival]), object(), fake_day_factory('low'), fib, curve)
        self.assertTrue(clean['projected_gross'] > crowded['projected_gross'])
        self.assertEqual(crowded['visible_rival_supply_bound'], 11)

    def test_custom_curve_passthrough_is_identity_safe(self):
        record = gate.evaluate(obs(price=130), object(), fake_day_factory('low'), fib,
                               lambda item, inv: 129)
        self.assertIsNone(record['decision'])
        self.assertEqual(record['reason'], 'custom_market_curve')


if __name__ == '__main__':
    unittest.main()
