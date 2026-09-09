from copy import deepcopy
import unittest

from opening_turnover import prioritize_opening_seeds


class M:
    CROPS = {
        'WHEAT': {'seed': 10}, 'CARROT': {'seed': 20},
        'TOMATO': {'seed': 50}, 'STRAWBERRY': {'seed': 100},
        'MELON': {'seed': 80},
    }
    ANIMALS = {'GOOSE': {'cost': 300}, 'COW': {'cost': 400}, 'SHEEP': {'cost': 500}}
    LAND_PRICES = [1000, 2000, 4000]

    @staticmethod
    def _hire_cost(n, mult=1):
        a, b = 1, 1
        for _ in range(n):
            a, b = b, a + b
        return mult * a


def obs(money=55, step=0, hires=0):
    farm = {'money': money, 'hires_today': hires, 'unlocked_quadrants': ['NW']}
    return {'step': step, 'player': 0, 'farms': [farm, deepcopy(farm)], 'private': {}}


def action(market):
    return {'farmer': ['PASS'], 'hands': [['PASS']], 'market': market, 'tag': {'keep': 1}}


class OpeningTurnoverTests(unittest.TestCase):
    def test_annual_priority_preserves_hire_slot_and_selects_wheat(self):
        src = action([['BUY_SEED', 'TOMATO', 1], ['HIRE'], ['BUY_SEED', 'WHEAT', 1], ['BUY_LAND']])
        got, report = prioritize_opening_seeds(M, obs(55), {}, src, mode='annual')
        self.assertTrue(report['changed'])
        self.assertEqual(got['market'][:3], [['BUY_SEED', 'WHEAT', 1], ['HIRE'], ['BUY_SEED', 'TOMATO', 1]])
        self.assertEqual(got['market'][1], ['HIRE'])
        self.assertEqual(report['certificate_cost'], 11)
        self.assertEqual(src['market'][0], ['BUY_SEED', 'TOMATO', 1])

    def test_refuses_when_promoted_seed_plus_hire_not_funded(self):
        src = action([['BUY_SEED', 'TOMATO', 1], ['HIRE'], ['BUY_SEED', 'WHEAT', 1], ['BUY_LAND']])
        got, report = prioritize_opening_seeds(M, obs(10), {}, src, mode='wheat')
        self.assertIs(got, src)
        self.assertFalse(report['changed'])
        self.assertEqual(report['reason'], 'target_or_hire_prefix_not_funded')

    def test_fully_funded_queue_is_exact_noop(self):
        src = action([['BUY_SEED', 'TOMATO', 1], ['BUY_SEED', 'WHEAT', 1]])
        got, report = prioritize_opening_seeds(M, obs(60), {}, src, mode='wheat')
        self.assertIs(got, src)
        self.assertEqual(report['reason'], 'queue_already_fully_funded_without_sales')

    def test_variable_product_price_fails_closed(self):
        src = action([['BUY_SEED', 'TOMATO', 1], ['BUY_PRODUCT', 'WHEAT', 1], ['BUY_SEED', 'WHEAT', 1]])
        got, report = prioritize_opening_seeds(M, obs(100), {}, src, mode='annual')
        self.assertIs(got, src)
        self.assertIn('variable-price', report['reason'])

    def test_outside_opening_window_is_noop(self):
        src = action([['BUY_SEED', 'TOMATO', 1], ['BUY_SEED', 'WHEAT', 1]])
        got, report = prioritize_opening_seeds(M, obs(10, step=264), {}, src)
        self.assertIs(got, src)
        self.assertEqual(report['reason'], 'outside_opening_window')

    def test_carrot_mode_promotes_only_carrot(self):
        src = action([['BUY_SEED', 'WHEAT', 1], ['BUY_SEED', 'TOMATO', 1], ['BUY_SEED', 'CARROT', 1], ['BUY_LAND']])
        got, report = prioritize_opening_seeds(M, obs(30), {}, src, mode='carrot')
        self.assertTrue(report['changed'])
        self.assertEqual(got['market'][0], ['BUY_SEED', 'CARROT', 1])
        self.assertEqual(report['certificate_cost'], 20)

    def test_executable_tail_is_byte_for_byte_preserved(self):
        prefix = [['BUY_SEED', 'TOMATO', 1], ['BUY_SEED', 'WHEAT', 1]]
        tail = [['BUY_SEED', 'CARROT', 999], ['UNKNOWN', {'opaque': True}]]
        cfg = {'maxMarketOrdersPerTurn': 2}
        src = action(prefix + tail)
        got, report = prioritize_opening_seeds(M, obs(10), cfg, src, mode='wheat')
        self.assertTrue(report['changed'])
        self.assertEqual(got['market'][2:], tail)

    def test_hire_indices_and_non_market_fields_are_invariant(self):
        src = action([['BUY_SEED', 'TOMATO', 1], ['HIRE'], ['BUY_SEED', 'WHEAT', 1], ['HIRE'], ['BUY_LAND']])
        got, report = prioritize_opening_seeds(M, obs(62), {}, src, mode='annual')
        self.assertTrue(report['changed'])
        self.assertEqual([i for i,o in enumerate(src['market']) if o[0]=='HIRE'],
                         [i for i,o in enumerate(got['market']) if o[0]=='HIRE'])
        self.assertEqual({k:v for k,v in src.items() if k!='market'},
                         {k:v for k,v in got.items() if k!='market'})

    def test_unknown_mode_and_crop_fail_closed(self):
        src = action([['BUY_SEED', 'TOMATO', 1], ['BUY_SEED', 'WHEAT', 1]])
        self.assertFalse(prioritize_opening_seeds(M, obs(10), {}, src, mode='bogus')[1]['changed'])
        bad = action([['BUY_SEED', 'UNKNOWN', 1], ['BUY_SEED', 'WHEAT', 1]])
        got, report = prioritize_opening_seeds(M, obs(10), {}, bad)
        self.assertIs(got, bad)
        self.assertEqual(report['reason'], 'unknown seed crop')

    def test_zero_quantity_rows_are_not_permuted(self):
        src = action([['BUY_SEED', 'TOMATO', 1], ['BUY_SEED', 'WHEAT', 0], ['BUY_SEED', 'CARROT', 1]])
        got, report = prioritize_opening_seeds(M, obs(20), {}, src, mode='wheat')
        self.assertIs(got, src)
        self.assertEqual(report['reason'], 'no_mixed_target_seed_frontier')


if __name__ == '__main__':
    unittest.main()
