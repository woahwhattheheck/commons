# SPDX-License-Identifier: Apache-2.0
"""Engine invariant and physical-certificate tests for alternate feed."""
from copy import deepcopy
import unittest

import mechanics as m
from alternate_feed import propose_alternate_day_feed


class AlternateFeedEngineTests(unittest.TestCase):
    def animal_farm(self):
        return {'tiles': [[m._new_animal('GOOSE', 0)]]}

    def test_first_unfed_refresh_survives_and_keeps_base_yield(self):
        farm = self.animal_farm()
        m._daily_refresh_animals(farm, 3)  # next_day=4, first goose yield day
        tile = farm['tiles'][0][0]
        self.assertEqual(tile['animal'], 'GOOSE')
        self.assertEqual(tile['consecutive_unfed'], 1)
        self.assertEqual(tile['yield_units'], 1)

    def test_second_consecutive_unfed_refresh_escapes_before_yield(self):
        farm = self.animal_farm()
        m._daily_refresh_animals(farm, 3)
        m._daily_refresh_animals(farm, 4)
        self.assertEqual(farm['tiles'][0][0], {'kind': 'COOP'})

    def test_unfed_production_day_does_not_receive_pending_care_bonus(self):
        farm = self.animal_farm()
        farm['tiles'][0][0]['pending_care_bonus'] = 1
        m._daily_refresh_animals(farm, 3)
        tile = farm['tiles'][0][0]
        self.assertEqual(tile['yield_units'], 1)
        self.assertEqual(tile['pending_care_bonus'], 0)

    def test_fed_production_day_receives_pending_care_bonus(self):
        farm = self.animal_farm()
        tile = farm['tiles'][0][0]
        tile['pending_care_bonus'] = 1
        tile['fed_today'] = True
        m._daily_refresh_animals(farm, 3)
        tile = farm['tiles'][0][0]
        self.assertEqual(tile['yield_units'], 2)
        self.assertEqual(tile['consecutive_unfed'], 0)


class AlternateFeedProposalTests(unittest.TestCase):
    def setUp(self):
        self.farm = {
            'farmer': [4, 4], 'hands': [], 'money': 1000,
            'hires_today': 0, 'unlocked_quadrants': ['NW'],
            'tiles': [[None for _ in range(10)] for _ in range(10)],
        }
        self.farm['tiles'][4][4] = m._new_animal('GOOSE', 0)
        self.private = {
            'shed': {'WHEAT': 2},
            'inventories': [{'WHEAT': 1}],
            'seeds': {},
        }
        rival = {'tiles': [[None for _ in range(10)] for _ in range(10)]}
        self.obs = {
            'step': 23, 'day': 0, 'hour': 23, 'player': 0,
            'farms': [self.farm, rival], 'private': self.private,
            'market': {'inventory': {'WHEAT': 10000}},
        }
        self.selected = {'farmer': ['FEED'], 'hands': [], 'market': []}
        self.route = [
            {'farmer': ['PASS'], 'hands': [], 'market': []}
            for _ in range(720)
        ]
        # Day reset respawns the main farmer at (4,4), which is also shed access.
        self.route[24]['farmer'] = ['PICKUP', 'WHEAT', 1]
        self.route[25]['farmer'] = ['FEED']

    def post_snapshot(self):
        farm = deepcopy(self.farm)
        private = deepcopy(self.private)
        actions = [self.selected.get('farmer') or ['PASS'],
                   *(self.selected.get('hands') or [])]
        for actor, action in enumerate(actions):
            m._apply_unit_action(farm, private, actor, action, 10, 0, 24, 100)
        return farm, private

    def propose(self, checkpoints=()):
        post_farm, post_private = self.post_snapshot()
        return propose_alternate_day_feed(
            m, self.obs, {}, self.selected, post_farm, post_private,
            self.route, checkpoints,
        )

    def unchanged(self, reason):
        result, report = self.propose()
        self.assertIs(result, self.selected)
        self.assertFalse(report['changed'])
        self.assertFalse(report['certified'])
        self.assertEqual(report['reason'], reason)

    def test_certified_day_close_feed_becomes_pass(self):
        before = deepcopy((self.obs, self.selected, self.route))
        result, report = self.propose()
        self.assertEqual(result['farmer'], ['PASS'])
        self.assertEqual(result['market'], [])
        self.assertTrue(report['changed'])
        self.assertTrue(report['certified'])
        self.assertEqual(report['saved_wheat_units'], 1)
        self.assertEqual(report['required_next_day_wheat'], 1)
        self.assertEqual(report['saved_wheat_rescue_credit'], 0)
        self.assertEqual(report['future_purchase_credit'], 0)
        self.assertEqual((self.obs, self.selected, self.route), before)

    def test_only_day_close_can_use_the_one_miss_boundary(self):
        self.obs['step'] = 22
        self.obs['hour'] = 22
        self.unchanged('alternate_feed_is_day_close_only')

    def test_prior_miss_is_never_extended_to_two(self):
        self.farm['tiles'][4][4]['consecutive_unfed'] = 1
        self.unchanged('no_safe_day_close_feed')
        self.assertEqual(self.propose()[1]['targets'][0]['reason'],
                         'animal_already_missed_feed')

    def test_existing_or_same_turn_care_value_keeps_feed(self):
        self.farm['tiles'][4][4]['cared_today'] = True
        self.unchanged('no_safe_day_close_feed')
        self.farm['tiles'][4][4]['cared_today'] = False
        self.farm['tiles'][4][4]['pending_care_bonus'] = 1
        self.unchanged('no_safe_day_close_feed')
        self.farm['tiles'][4][4]['pending_care_bonus'] = 0

        self.farm['hands'] = [[4, 4]]
        self.private['inventories'].append({})
        self.selected['hands'] = [['CARE']]
        self.unchanged('no_safe_day_close_feed')
        self.assertEqual(self.propose()[1]['targets'][0]['reason'],
                         'same_turn_care_requires_feed')

    def test_duplicate_feed_on_one_target_is_not_reinterpreted(self):
        self.farm['hands'] = [[4, 4]]
        self.private['inventories'].append({'WHEAT': 1})
        self.selected['hands'] = [['FEED']]
        self.unchanged('no_safe_day_close_feed')
        self.assertEqual(self.propose()[1]['targets'][0]['reason'],
                         'shared_feed_target')

    def test_incumbent_feed_must_have_really_succeeded(self):
        self.private['inventories'][0] = {}
        self.unchanged('no_safe_day_close_feed')
        self.assertEqual(self.propose()[1]['targets'][0]['reason'],
                         'incumbent_feed_not_proven')

    def test_same_animal_must_have_a_certified_next_day_rescue(self):
        self.route[25]['farmer'] = ['PASS']
        self.unchanged('no_certified_next_day_rescue')

    def test_current_sales_cannot_be_ignored_when_funding_rescue(self):
        self.selected['market'] = [['SELL', 'WHEAT', 2]]
        self.unchanged('next_day_rescue_feed_not_prepaid')

    def test_future_sale_before_pickup_breaks_rescue_certificate(self):
        self.route[24]['farmer'] = ['PASS']
        self.route[24]['market'] = [['SELL', 'WHEAT', 1]]
        self.route[25]['farmer'] = ['PICKUP', 'WHEAT', 1]
        self.route[26]['farmer'] = ['FEED']
        self.unchanged('intervening_wheat_sale_before_protected_pickup')

    def test_saved_wheat_must_fit_the_end_of_day_delivery(self):
        self.private['shed'] = {'WHEAT': 100}
        self.unchanged('saved_wheat_would_overflow_at_reset')

    def test_route_checkpoint_declines_uncertified_future(self):
        self.unchanged('unresolved_feed_window') if False else None
        result, report = self.propose(checkpoints=(25,))
        self.assertIs(result, self.selected)
        self.assertEqual(report['reason'], 'unresolved_feed_window')

    def test_nonstandard_clock_and_late_episode_decline(self):
        post_farm, post_private = self.post_snapshot()
        result, report = propose_alternate_day_feed(
            m, self.obs, {'turnsPerDay': 12}, self.selected,
            post_farm, post_private, self.route, (),
        )
        self.assertIs(result, self.selected)
        self.assertEqual(report['reason'], 'outside_supported_alternate_feed_window')
        self.obs['step'] = 695
        self.unchanged('outside_supported_alternate_feed_window')


if __name__ == '__main__':
    unittest.main(verbosity=2)
