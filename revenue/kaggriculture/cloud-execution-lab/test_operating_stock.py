# SPDX-License-Identifier: Apache-2.0
"""Stateless proposal contracts. No agent turn or game transition is executed."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

import mechanics as m
from operating_stock import protect_operating_stock
from titan_runtime import Features, TitanAgent


class OperatingStockTests(unittest.TestCase):
    def setUp(self):
        self.now = 460
        self.farm = {'farmer': [4, 4], 'hands': [[4, 4]], 'money': 50000,
                     'tiles': [[None for _ in range(10)] for _ in range(10)]}
        for x in (2, 3):
            self.farm['tiles'][4][x] = {
                'kind': 'PLANT', 'crop': 'STRAWBERRY', 'planted_day': 11,
                'yield_units': 0, 'fertilized_until_day': -1, 'max_lifespan_step': -1,
                'consecutive_unwatered': 0, 'watered_today': False}
        self.private = {'inventories': [{}, {}], 'shed': {'FERTILIZER': 9}, 'seeds': {}}
        self.obs = {'step': self.now, 'player': 0, 'day': 19,
                    'market': {'inventory': {'FERTILIZER': 10300, 'STRAWBERRY': 9900}}}
        self.selected = {'farmer': ['PASS'], 'hands': [['PASS']],
                         'market': [['SELL', 'FERTILIZER', 9]]}
        self.route = [{'farmer': ['PASS'], 'hands': [['PASS']], 'market': []}
                      for _ in range(720)]
        self.route[461]['hands'][0] = ['PICKUP', 'FERTILIZER', 3]
        self.route[462]['hands'][0] = ['WEST']
        self.route[463]['hands'][0] = ['FERTILIZE']
        self.route[464]['hands'][0] = ['WEST']
        self.route[465]['hands'][0] = ['FERTILIZE']

    def propose(self, checkpoints=(226, 360, 433), config=None):
        return protect_operating_stock(m, self.obs, config or {}, self.selected,
                                       self.farm, self.private, self.route, checkpoints)

    def unchanged(self, reason=None, **kwargs):
        result, report = self.propose(**kwargs)
        self.assertIs(result, self.selected)
        self.assertFalse(report['changed'])
        if reason:
            self.assertEqual(report['reason'], reason)

    def test_reserve_actual_consumption_not_oversized_pickup_request(self):
        original = deepcopy((self.farm, self.private, self.selected, self.route))
        result, report = self.propose()
        self.assertEqual(result['market'], [['SELL', 'FERTILIZER', 7]])
        self.assertEqual(report['required_stock'], 2)
        self.assertEqual(report['pickup_step'], 461)
        self.assertEqual(len(report['obligations']), 2)
        self.assertFalse(report['future_cash_gain_measured'])
        self.assertEqual((self.farm, self.private, self.selected, self.route), original)

    def test_slots_other_products_and_units_are_preserved(self):
        self.selected['market'] = [['SELL', 'FERTILIZER', 4], ['SELL', 'WOOL', 8],
                                   [], ['SELL', 'FERTILIZER', 5]]
        self.selected['farmer'] = ['CARE']
        result, _ = self.propose()
        self.assertEqual(result['market'], [['SELL', 'FERTILIZER', 4], ['SELL', 'WOOL', 8],
                                            [], ['SELL', 'FERTILIZER', 3]])
        self.assertEqual(result['farmer'], self.selected['farmer'])
        self.assertEqual(result['hands'], self.selected['hands'])

    def test_zero_sale_keeps_its_slot(self):
        self.private['shed']['FERTILIZER'] = 2
        self.selected['market'] = [['SELL', 'FERTILIZER', 2], ['SELL', 'WOOL', 1]]
        result, _ = self.propose()
        self.assertEqual(result['market'], [[], ['SELL', 'WOOL', 1]])

    def test_carried_fertilizer_reduces_shed_obligation(self):
        self.private['inventories'][1]['FERTILIZER'] = 1
        result, report = self.propose()
        self.assertEqual(report['required_stock'], 1)
        self.assertEqual(result['market'], [['SELL', 'FERTILIZER', 8]])
        self.private['inventories'][1]['FERTILIZER'] = 2
        self.unchanged()

    def test_no_obligation_after_pickup_passed(self):
        self.obs['step'] = 462
        self.unchanged('requires_one_unambiguous_pickup')

    def test_no_missing_worker_or_unreachable_pickup(self):
        self.farm['hands'] = []
        self.unchanged('requires_one_unambiguous_pickup')
        self.farm['hands'] = [[0, 0]]
        self.unchanged('pickup_not_reachable_from_shed')

    def test_competing_pickup_does_not_invent_shared_allocation(self):
        self.route[462]['farmer'] = ['PICKUP', 'FERTILIZER', 1]
        self.unchanged('requires_one_unambiguous_pickup')

    def test_no_current_or_future_hiring_boundary(self):
        self.selected['market'].append(['HIRE'])
        self.unchanged('current_hiring_boundary')
        self.selected['market'].pop()
        self.route[462]['market'] = [['HIRE']]
        self.unchanged('no_distinct_useful_consumption')

    def test_branch_and_reset_cut_off_future_consumption(self):
        self.unchanged(checkpoints=(462,))
        for step in (461, 462, 463, 464, 465):
            self.route[step]['hands'][0] = ['PASS']
        self.route[478]['hands'][0] = ['PICKUP', 'FERTILIZER', 3]
        self.route[479]['hands'][0] = ['FERTILIZE']
        self.unchanged('no_distinct_useful_consumption')

    def test_no_credit_for_requested_purchase_or_input_deposit(self):
        self.route[461]['market'] = [['BUY_PRODUCT', 'FERTILIZER', 3]]
        self.unchanged('intervening_requested_replenishment')
        self.route[461]['market'] = []
        self.route[460 + 1]['farmer'] = ['PLACE', 'FERTILIZER', 1]
        self.route[461]['hands'][0] = ['PASS']
        self.route[462]['hands'][0] = ['PICKUP', 'FERTILIZER', 3]
        self.route[463]['hands'][0] = ['WEST']
        self.route[464]['hands'][0] = ['FERTILIZE']
        self.route[465]['hands'][0] = ['WEST']
        self.route[466]['hands'][0] = ['FERTILIZE']
        self.unchanged('intervening_requested_input_deposit')

    def test_capacity_does_not_use_later_sell_as_room(self):
        self.private['shed']['WOOL'] = 90
        self.route[462]['farmer'] = ['PLACE', 'WOOL', 2]
        self.route[462]['market'] = [['SELL', 'WOOL', 90]]
        self.unchanged('retained_stock_conflicts_with_arrival_room')

    def test_current_animal_purchase_is_in_arrival_bound(self):
        self.selected['market'].append(['BUY_ANIMAL', 'COW', 100])
        self.unchanged('retained_stock_conflicts_with_arrival_room')

    def test_current_cash_funds_later_orders_without_sale_credit(self):
        self.selected['market'].append(['BUY_SEED', 'STRAWBERRY', 20])
        self.farm['money'] = 2100
        self.unchanged('actual_cash_cushion_insufficient')
        self.farm['money'] = 10000
        result, report = self.propose()
        self.assertTrue(report['changed'])
        self.assertEqual(result['market'][1], ['BUY_SEED', 'STRAWBERRY', 20])
        self.assertEqual(self.farm['money'], 10000)

    def test_variable_purchase_keeps_incumbent_funding(self):
        self.route[464]['market'] = [['BUY_PRODUCT', 'WHEAT', 3]]
        self.unchanged('intervening_variable_price_purchase')

    def test_no_obsolete_fertility_or_duplicate_service(self):
        self.farm['tiles'][4][3]['fertilized_until_day'] = 21
        self.unchanged('pickup_suffix_contains_nonproductive_consumption')
        self.farm['tiles'][4][3]['fertilized_until_day'] = -1
        self.route[464]['hands'][0] = ['PASS']
        self.unchanged('no_distinct_useful_consumption')

    def test_no_removed_or_shared_target(self):
        self.route[461]['farmer'] = ['WEST']
        self.route[464]['farmer'] = ['FERTILIZE']
        self.unchanged('target_has_competing_asset_or_input_action')
        self.route[464]['farmer'] = ['DIG']
        self.unchanged('target_has_competing_asset_or_input_action')

    def test_water_before_reset_is_a_real_prerequisite(self):
        self.farm['tiles'][4][3]['consecutive_unwatered'] = 1
        self.unchanged('target_lacks_water_before_reset')
        self.route[461]['farmer'] = ['WEST']
        self.route[466]['farmer'] = ['WATER']
        result, report = self.propose()
        self.assertTrue(report['changed'])

    def test_glutted_product_and_exhausted_crop_do_not_hold_inputs(self):
        self.obs['market']['inventory']['STRAWBERRY'] = 11000
        self.unchanged('marginal_product_screen_not_favorable')
        self.obs['market']['inventory']['STRAWBERRY'] = 9900
        self.farm['tiles'][4][3]['yield_units'] = 4
        self.unchanged('pickup_suffix_contains_nonproductive_consumption')

    def test_terminal_and_nonstandard_clock_preserve_action(self):
        self.obs['step'] = 698
        self.unchanged('outside_supported_production_window')
        self.obs['step'] = 460
        self.unchanged('outside_supported_production_window', config={'turnsPerDay': 12})

    def test_runtime_boundary_uses_snapshot_and_same_controller(self):
        agent = TitanAgent(Features(operating_stock=True))
        agent.consumer = SimpleNamespace(selected_post_units=(self.farm, self.private))
        agent.controller = SimpleNamespace(cur='case', R={'case': self.route})
        agent.selected = deepcopy(self.selected)
        result = agent._operating_stock_selected(self.obs, {}, self.selected)
        self.assertEqual(result['market'], [['SELL', 'FERTILIZER', 7]])
        self.assertTrue(agent.diagnostics['operating_stock']['changed'])
        other_units = deepcopy(self.selected)
        other_units['farmer'] = ['NORTH']
        self.assertIs(agent._operating_stock_selected(self.obs, {}, other_units), other_units)
        agent.consumer.selected_post_units = None
        self.assertIs(agent._operating_stock_selected(self.obs, {}, self.selected), self.selected)
        agent.features = Features(operating_stock=False)
        self.assertIs(agent._operating_stock_selected(self.obs, {}, self.selected), self.selected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
