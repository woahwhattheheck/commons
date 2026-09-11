from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import candidate as b6  # noqa: E402


PRODUCTS = tuple(b6.base.PRODUCTS)
BLANK = {"farmer": ["PASS"], "hands": [], "market": []}


class FakeTape:
    def __init__(self, events=None):
        self.events = dict(events or {})

    def __getitem__(self, step):
        return self.events.get(step, BLANK)


class FakePolicy:
    def __init__(self):
        self.tapes = [FakeTape() for _ in range(13)]


def observation(step=300, *, shed=None, prices=None, inventory=None):
    shed_values = {item: 0 for item in PRODUCTS}
    shed_values.update(shed or {})
    price_values = {item: 100 for item in PRODUCTS}
    price_values.update(prices or {})
    tiles = [[None for _ in range(10)] for _ in range(10)]
    return {
        "step": step,
        "player": 0,
        "farms": [{
            "tiles": tiles,
            "farmer": [4, 4],
            "hands": [],
            "money": 10000,
        }],
        "private": {
            "inventories": [dict(inventory or {})],
            "shed": shed_values,
        },
        "market": {"prices": price_values, "inventory": {}},
        "town": {"unlocked_shops": []},
    }


def action(*, market=None, farmer=None):
    return {
        "farmer": list(farmer or ["PASS"]),
        "hands": [],
        "market": [list(row) if row else row for row in (market or [])],
    }


def state(plan=5, queues=None):
    return SimpleNamespace(plan=plan, queues=dict(queues or {}))


class DeadStockSweepTests(unittest.TestCase):
    def setUp(self):
        b6.reset_b6_report()
        self.policy = FakePolicy()

    def sweep(self, obs, parent, *, st=None, enabled=True):
        return b6.dead_stock_sweep(
            obs,
            parent,
            policy=self.policy,
            state=st or state(),
            enabled=enabled,
        )

    def test_exact_v31_baseline_is_pinned(self):
        self.assertEqual(b6.base.SALE_HORIZON, 8)
        self.assertEqual(b6.base.OPEN_ROUNDTRIP, 0)
        self.assertIs(b6.base.ROW_ORDER, True)
        self.assertIs(b6.base.EVENING_FLUSH, True)
        self.assertEqual(b6.base.SALE_EXCLUDED, ("WHEAT",))
        self.assertIs(b6.base._V231_EARLY, True)

    def test_disabled_before_route_and_terminal_are_identity(self):
        original = action()
        self.assertIs(self.sweep(observation(shed={"CARROT": 4}), original, enabled=False), original)
        self.assertIs(self.sweep(observation(step=143, shed={"CARROT": 4}), original), original)
        self.assertIs(
            self.sweep(observation(step=b6.base.LAST_STEP, shed={"CARROT": 4}), original),
            original,
        )
        self.assertEqual(b6.B6_REPORT["activations"], 0)

    def test_dead_products_sell_but_dynamic_consumers_are_permanently_reserved(self):
        obs = observation(
            shed={"CARROT": 4, "EGG": 2, "WHEAT": 9, "FERTILIZER": 7},
            prices={"CARROT": 35, "EGG": 50, "WHEAT": 25, "FERTILIZER": 100},
        )
        result = self.sweep(obs, action())
        self.assertEqual(result["market"], [["SELL", "CARROT", 4], ["SELL", "EGG", 2]])
        self.assertEqual(b6.B6_REPORT["units_advanced"], 6)
        self.assertEqual(b6.B6_REPORT["posted_quote_value"], 240)

    def test_future_pickup_in_active_plan_vetoes_entire_item(self):
        self.policy.tapes[5] = FakeTape({301: {
            "farmer": ["PICKUP", "CARROT", 1], "hands": [], "market": []
        }})
        obs = observation(step=300, shed={"CARROT": 8, "EGG": 2})
        result = self.sweep(obs, action(), st=state(plan=5))
        self.assertEqual(result["market"], [["SELL", "EGG", 2]])
        self.assertEqual(b6.B6_REPORT["native_consumer_blocks"], 1)

    def test_forced_plan2_future_is_scanned_after_step648_boundary(self):
        self.policy.tapes[5] = FakeTape()
        self.policy.tapes[2] = FakeTape({650: {
            "farmer": ["PICKUP", "MILK", 1], "hands": [], "market": []
        }})
        obs = observation(step=600, shed={"MILK": 5, "EGG": 1})
        result = self.sweep(obs, action(), st=state(plan=5))
        self.assertEqual(result["market"], [["SELL", "EGG", 1]])

    def test_after_final_plan_step_only_plan2_matters(self):
        self.policy.tapes[5] = FakeTape({700: {
            "farmer": ["PICKUP", "CARROT", 1], "hands": [], "market": []
        }})
        self.policy.tapes[2] = FakeTape()
        obs = observation(step=649, shed={"CARROT": 3})
        result = self.sweep(obs, action(), st=state(plan=5))
        self.assertEqual(result["market"], [["SELL", "CARROT", 3]])

    def test_delayed_queue_pickup_vetoes_item(self):
        st = state(queues={0: [["PICKUP", "EGG", 1]], 1: [["PASS"]]})
        obs = observation(shed={"EGG": 5, "CARROT": 2})
        result = self.sweep(obs, action(), st=st)
        self.assertEqual(result["market"], [["SELL", "CARROT", 2]])
        self.assertEqual(b6.B6_REPORT["queued_consumer_blocks"], 1)

    def test_same_turn_buy_product_vetoes_accidental_round_trip_and_parent_index_is_stable(self):
        parent = action(market=[["BUY_PRODUCT", "TOMATO", 2]])
        obs = observation(shed={"TOMATO": 4, "EGG": 1})
        result = self.sweep(obs, parent)
        self.assertEqual(result["market"], [["BUY_PRODUCT", "TOMATO", 2], ["SELL", "EGG", 1]])
        self.assertEqual(result["market"][0], parent["market"][0])
        self.assertEqual(b6.B6_REPORT["same_turn_buy_blocks"], 1)

    def test_existing_parent_sell_is_subtracted_and_parent_indices_stay_fixed(self):
        parent = action(market=[["SELL", "CARROT", 2], ["BUY_SEED", "WHEAT", 1]])
        obs = observation(shed={"CARROT": 5}, prices={"CARROT": 35})
        result = self.sweep(obs, parent)
        self.assertEqual(
            result["market"],
            [["SELL", "CARROT", 2], ["BUY_SEED", "WHEAT", 1], ["SELL", "CARROT", 3]],
        )
        self.assertEqual(result["market"][:2], parent["market"])

    def test_empty_parent_placeholder_is_preserved_at_same_index(self):
        parent = action(market=[[], ["BUY_SEED", "WHEAT", 1]])
        obs = observation(shed={"CARROT": 2})
        result = self.sweep(obs, parent)
        self.assertEqual(
            result["market"],
            [[], ["BUY_SEED", "WHEAT", 1], ["SELL", "CARROT", 2]],
        )
        self.assertEqual(result["market"][:2], parent["market"])

    def test_current_pickup_is_projected_before_sweeping_remainder(self):
        parent = action(farmer=["PICKUP", "CARROT", 2])
        obs = observation(shed={"CARROT": 5})
        result = self.sweep(obs, parent)
        self.assertEqual(result["market"], [["SELL", "CARROT", 3]])
        self.assertEqual(result["farmer"], ["PICKUP", "CARROT", 2])

    def test_full_order_cap_declines_without_mutating_parent(self):
        full = [["BUY_SEED", "WHEAT", 1] for _ in range(b6.base.MAX_ORDERS)]
        parent = action(market=full)
        obs = observation(shed={"CARROT": 5})
        self.assertIs(self.sweep(obs, parent), parent)
        self.assertEqual(b6.B6_REPORT["capacity_declines"], 1)
        self.assertEqual(b6.B6_REPORT["activations"], 0)

    def test_partial_order_capacity_keeps_parent_indices_and_picks_best_extra(self):
        parent_rows = [["BUY_SEED", "WHEAT", 1] for _ in range(b6.base.MAX_ORDERS - 1)]
        parent = action(market=parent_rows)
        obs = observation(
            shed={"CARROT": 10, "EGG": 5, "MELON": 1},
            prices={"CARROT": 35, "EGG": 50, "MELON": 250},
        )
        result = self.sweep(obs, parent)
        self.assertEqual(result["market"][:-1], parent_rows)
        # CARROT current quote-value 350 beats EGG/MELON 250 for the only trailing slot.
        self.assertEqual(result["market"][-1], ["SELL", "CARROT", 10])
        self.assertEqual(len(result["market"]), b6.base.MAX_ORDERS)
        self.assertEqual(b6.B6_REPORT["capacity_declines"], 1)

    def test_price_floor_keeps_stock_when_quote_is_one(self):
        parent = action()
        obs = observation(shed={"CARROT": 5}, prices={"CARROT": 1})
        self.assertIs(self.sweep(obs, parent), parent)
        self.assertEqual(b6.B6_REPORT["activations"], 0)


if __name__ == "__main__":
    unittest.main()
