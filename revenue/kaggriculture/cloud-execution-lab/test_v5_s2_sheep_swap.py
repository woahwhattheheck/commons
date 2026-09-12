from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

LAB = Path(__file__).resolve().parent
CANDIDATE = LAB / 'candidates/v5/s2-milk-shop-gated'
if str(CANDIDATE) not in sys.path:
    sys.path.insert(0, str(CANDIDATE))
import v5_s2_adapter as adapter

CFG = dict(episodeSteps=720, boardSize=10, turnsPerDay=24,
           shedCapacity=100, maxMarketOrdersPerTurn=10)


def action(market=None, farmer=None, hands=None):
    return {'farmer': farmer or ['PASS'], 'hands': hands or [['PASS']], 'market': market or []}


def tape(step=100, future=None):
    rows = [action() for _ in range(719)]
    rows[step] = action([['BUY_ANIMAL', 'COW', 1]])
    for offset, value in (future or {}).items():
        rows[step + offset] = value
    return rows


def obs(step=100, *, shops=None, prices=None, money=1000, shed=None, invs=None):
    board = [[{} for _ in range(10)] for _ in range(10)]
    return {
        'step': step,
        'player': 0,
        'farms': [
            {'money': money, 'tiles': board, 'farmer': [4, 4], 'hands': [[4, 4]], 'hires_today': 0},
            {'money': 1000, 'tiles': [[{} for _ in range(10)] for _ in range(10)],
             'farmer': [4, 4], 'hands': [[4, 4]], 'hires_today': 0},
        ],
        'private': {'shed': {} if shed is None else shed,
                    'inventories': [{}, {}] if invs is None else invs},
        'town': {'unlocked_shops': ['YARN_STORE'] if shops is None else shops},
        'market': {'prices': {'WOOL': 200, 'MILK': 100} if prices is None else prices},
    }


def agent(route, *, consumer='frozen', terminal_route=False):
    return SimpleNamespace(
        features=SimpleNamespace(consumer=consumer, terminal_route=terminal_route),
        controller=SimpleNamespace(R=[route], cur=0),
    )


class CurrentV5S2AdapterTests(unittest.TestCase):
    def test_disabled_is_exact_selected_identity(self):
        selected = action([['BUY_ANIMAL', 'COW', 1]])
        result, report = adapter.apply_current_v5(agent(tape()), obs(), CFG, selected, enabled=False)
        self.assertIs(result, selected)
        self.assertEqual(report['reason'], 'disabled')

    def test_positive_gate_rewrites_exact_cow_buy(self):
        selected = action([['BUY_ANIMAL', 'COW', 1]])
        result, report = adapter.apply_current_v5(agent(tape()), obs(), CFG, selected, enabled=True)
        self.assertEqual(result['market'], [['BUY_ANIMAL', 'SHEEP', 1]])
        self.assertEqual(selected['market'], [['BUY_ANIMAL', 'COW', 1]])
        self.assertTrue(report['applied'])

    def test_milk_shop_vetoes(self):
        selected = action([['BUY_ANIMAL', 'COW', 1]])
        result, report = adapter.apply_current_v5(
            agent(tape()), obs(shops=['YARN_STORE', 'PIZZA_SHOP']), CFG, selected, enabled=True)
        self.assertIs(result, selected)
        self.assertEqual(report['reason'], 'donor-noop')

    def test_wool_below_milk_vetoes(self):
        selected = action([['BUY_ANIMAL', 'COW', 1]])
        result, _ = adapter.apply_current_v5(
            agent(tape()), obs(prices={'WOOL': 99, 'MILK': 100}), CFG, selected, enabled=True)
        self.assertIs(result, selected)

    def test_future_same_day_purchase_vetoes(self):
        selected = action([['BUY_ANIMAL', 'COW', 1]])
        route = tape(future={1: action([['BUY_LAND', 'SE', 1]])})
        result, _ = adapter.apply_current_v5(agent(route), obs(), CFG, selected, enabled=True)
        self.assertIs(result, selected)

    def test_nonfrozen_and_terminal_routes_fail_closed(self):
        selected = action([['BUY_ANIMAL', 'COW', 1]])
        for kwargs in ({'consumer': 'ordered'}, {'terminal_route': True}):
            with self.subTest(kwargs=kwargs):
                result, report = adapter.apply_current_v5(agent(tape(), **kwargs), obs(), CFG,
                                                          selected, enabled=True)
                self.assertIs(result, selected)
                self.assertEqual(report['reason'], 'unsupported-current-route')

    def test_market_suffix_beyond_engine_prefix_fails_closed(self):
        selected = action([['BUY_ANIMAL', 'COW', 1]] + [['SELL', 'WHEAT', 1]] * 10)
        result, report = adapter.apply_current_v5(agent(tape()), obs(), CFG, selected, enabled=True)
        self.assertIs(result, selected)
        self.assertEqual(report['reason'], 'unsupported-market-prefix')

    def test_state_confirms_purchase_before_pickup_redirect(self):
        route = tape()
        a = agent(route)
        first = action([['BUY_ANIMAL', 'COW', 1]])
        out1, _ = adapter.apply_current_v5(a, obs(), CFG, first, enabled=True)
        self.assertEqual(out1['market'][0][1], 'SHEEP')
        route[101] = action(farmer=['PICKUP', 'COW', 1])
        second = action(farmer=['PICKUP', 'COW', 1])
        out2, report2 = adapter.apply_current_v5(
            a, obs(step=101, shed={'SHEEP': 1}), CFG, second, enabled=True)
        self.assertEqual(out2['farmer'], ['PICKUP', 'SHEEP', 1])
        self.assertTrue(report2['applied'])

    def test_enabled_requires_exact_bool(self):
        with self.assertRaises(TypeError):
            adapter.apply_current_v5(agent(tape()), obs(), CFG,
                                     action([['BUY_ANIMAL', 'COW', 1]]), enabled=1)


if __name__ == '__main__':
    unittest.main()
