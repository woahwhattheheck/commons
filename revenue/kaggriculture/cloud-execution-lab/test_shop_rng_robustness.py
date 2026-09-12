# SPDX-License-Identifier: Apache-2.0
"""Exact-source regressions for the end-of-day shop RNG research helper."""
import random
import unittest

import mechanics as m
from shop_rng_robustness import (
    ENGINE_SEED_MULTIPLIER,
    MAX_SHOP_INSTANCES,
    SHOP_ORDER,
    analyze_robust_shop,
    count_empty_tiles,
    shop_after_empty_draws,
    unlock_shop,
)


def reference_draw(seed, day, total_empty):
    """Literal pinned-engine cursor: N weed random() calls, then choice()."""
    rng = random.Random((seed * 1_000_003) ^ day)
    for _ in range(total_empty):
        rng.random()
    return rng.choice(sorted(m.SHOPS))


class ShopRngRobustnessTests(unittest.TestCase):
    def test_engine_constants_are_bound_to_pinned_source_values(self):
        self.assertEqual(ENGINE_SEED_MULTIPLIER, 1_000_003)
        self.assertEqual(MAX_SHOP_INSTANCES, 8)
        self.assertEqual(SHOP_ORDER, tuple(sorted(m.SHOPS)))

    def test_empty_count_matches_exact_spawn_weeds_rng_condition(self):
        tiles = [["LOCKED" for _ in range(10)] for _ in range(10)]
        tiles[0][0] = None
        tiles[0][1] = {'kind': 'WEED'}
        tiles[0][2] = {'kind': 'PLANT', 'crop': 'WHEAT'}
        tiles[0][3] = None
        self.assertEqual(count_empty_tiles({'tiles': tiles}), 2)
        with self.assertRaisesRegex(ValueError, 'unexpected_board_shape'):
            count_empty_tiles({'tiles': tiles[:-1]})

    def test_cursor_replay_matches_literal_python_engine_sequence(self):
        for seed in (0, 1, 17, 1909087201):
            for day in (2, 5, 11, 29):
                for total in (0, 1, 7, 50, 137, 200):
                    self.assertEqual(shop_after_empty_draws(seed, day, total),
                                     reference_draw(seed, day, total))

    def test_unlock_gate_uses_next_day_and_instance_cap(self):
        total = 80
        self.assertIsNone(unlock_shop(7, 1, total))  # next_day=2
        self.assertEqual(unlock_shop(7, 2, total), reference_draw(7, 2, total))
        self.assertIsNone(unlock_shop(7, 2, total, unlocked_count=8))
        self.assertEqual(unlock_shop(7, 4, total, unlock_interval=5),
                         reference_draw(7, 4, total))

    def test_single_supplied_rival_state_can_certify_exact_target(self):
        target = reference_draw(31, 2, 40)
        report = analyze_robust_shop(
            31, 2, 20, 20, [0], [0], target,
        )
        self.assertTrue(report['unlock_due'])
        self.assertEqual(report['robust_within_supplied_rival_bound'], [0])
        self.assertTrue(report['candidates'][0]['robust'])
        self.assertEqual(report['candidates'][0]['invariant_shop'], target)
        self.assertFalse(report['probability_model_used'])
        self.assertFalse(report['live_shop_payout_model_used'])

    def test_every_supplied_rival_delta_is_replayed_exactly(self):
        seed = 19
        report = analyze_robust_shop(
            seed, 2, 30, 40, [-2, 0, 3], [-1, 0, 2], 'BAKERY',
        )
        by_delta = {row['own_delta']: row for row in report['candidates']}
        for own_delta in (-2, 0, 3):
            outcomes = by_delta[own_delta]['outcomes']
            self.assertEqual([item['rival_delta'] for item in outcomes], [-1, 0, 2])
            for item in outcomes:
                expected_total = 30 + own_delta + 40 + item['rival_delta']
                self.assertEqual(item['total_empty_tiles'], expected_total)
                self.assertEqual(item['shop'], reference_draw(seed, 2, expected_total))
            expected_shops = sorted({item['shop'] for item in outcomes})
            self.assertEqual(by_delta[own_delta]['distinct_shops'], expected_shops)
            self.assertEqual(by_delta[own_delta]['robust'], expected_shops == ['BAKERY'])

    def test_expanding_rival_bound_can_destroy_a_narrow_certificate(self):
        # Find a deterministic adjacent cursor transition instead of baking in a
        # CPython Random output constant. The test still compares the exact
        # engine algorithm and fails if the analyzer omits the extra rival row.
        for seed in range(1000):
            narrow = reference_draw(seed, 2, 40)
            shifted = reference_draw(seed, 2, 41)
            if narrow != shifted:
                break
        else:
            self.fail('expected an adjacent shop cursor transition')
        one = analyze_robust_shop(seed, 2, 20, 20, [0], [0], narrow)
        two = analyze_robust_shop(seed, 2, 20, 20, [0], [0, 1], narrow)
        self.assertEqual(one['robust_within_supplied_rival_bound'], [0])
        self.assertEqual(two['robust_within_supplied_rival_bound'], [])
        self.assertEqual(two['reason'], 'no_target_robust_to_supplied_rival_bound')

    def test_non_unlock_day_and_cap_return_no_candidate_claim(self):
        report = analyze_robust_shop(3, 1, 20, 20, [0], [0], 'BAKERY')
        self.assertFalse(report['unlock_due'])
        self.assertEqual(report['candidates'], [])
        self.assertEqual(report['reason'], 'not_shop_unlock_day')
        report = analyze_robust_shop(
            3, 2, 20, 20, [0], [0], 'BAKERY', unlocked_count=8,
        )
        self.assertFalse(report['unlock_due'])
        self.assertEqual(report['reason'], 'shop_instance_cap_reached')

    def test_invalid_or_incomplete_physical_bounds_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'target_shop_not_in_engine_order'):
            analyze_robust_shop(1, 2, 20, 20, [0], [0], 'NOT_A_SHOP')
        with self.assertRaisesRegex(ValueError, 'own_legal_deltas_required'):
            analyze_robust_shop(1, 2, 20, 20, [], [0], 'BAKERY')
        with self.assertRaisesRegex(ValueError, 'rival_bounded_deltas_required'):
            analyze_robust_shop(1, 2, 20, 20, [0], [], 'BAKERY')
        with self.assertRaisesRegex(ValueError, 'own_delta_outside_board_capacity'):
            analyze_robust_shop(1, 2, 100, 20, [1], [0], 'BAKERY')
        with self.assertRaisesRegex(ValueError, 'rival_delta_outside_board_capacity'):
            analyze_robust_shop(1, 2, 20, 0, [0], [-1], 'BAKERY')


if __name__ == '__main__':
    unittest.main(verbosity=2)
