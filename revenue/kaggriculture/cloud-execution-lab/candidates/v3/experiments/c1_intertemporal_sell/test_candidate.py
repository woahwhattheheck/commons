from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("c1_candidate_tested", HERE / "candidate.py")
assert SPEC and SPEC.loader
c1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c1)


class SaleState:
    def __init__(self, *, advanced=None, debts=None):
        self.advanced_sales = {} if advanced is None else advanced
        self.sale_window_debts = {} if debts is None else debts


_DEFAULT = object()


def obs(*, shops=_DEFAULT, shed=_DEFAULT, inventories=_DEFAULT, step=308, player=0):
    return {
        "step": step,  # day12 hour20
        "player": player,
        "town": {"unlocked_shops": ["YARN_STORE"] if shops is _DEFAULT else shops},
        "farms": [{"money": 0}, {"money": 0}],
        "private": {
            "shed": {"WOOL": 9, "MILK": 3} if shed is _DEFAULT else shed,
            "inventories": [{}] if inventories is _DEFAULT else inventories,
        },
    }


def action(*, farmer=None, hands=None, market=None):
    return {
        "farmer": ["PASS"] if farmer is None else farmer,
        "hands": [] if hands is None else hands,
        "market": [["SELL", "WOOL", 9]] if market is None else market,
    }


class C1IntertemporalSellTests(unittest.TestCase):
    def setUp(self):
        c1.REPORT["callbacks"] = 0
        c1.REPORT["deferrals"] = 0
        c1.REPORT["deferred_rows"] = 0
        c1.REPORT["deferred_requested_qty"] = 0
        for item in c1.REPORT["by_item"]:
            c1.REPORT["by_item"][item] = 0

    def apply(self, observation, parent, *, native=None, state=None, configuration=None):
        return c1.apply_intertemporal_deferral(
            observation,
            parent,
            native_market=parent["market"] if native is None else native,
            sale_state=state,
            configuration=configuration,
        )

    def test_yarn_store_defers_native_wool_in_same_market_slot(self):
        parent = action(market=[[], ["SELL", "WOOL", 9], ["SELL", "MILK", 3]])
        result = self.apply(obs(), parent)
        self.assertIsNot(result, parent)
        self.assertEqual(result["market"], [[], [], ["SELL", "MILK", 3]])
        self.assertEqual(parent["market"], [[], ["SELL", "WOOL", 9], ["SELL", "MILK", 3]])
        self.assertEqual(c1.REPORT["deferrals"], 1)
        self.assertEqual(c1.REPORT["deferred_rows"], 1)
        self.assertEqual(c1.REPORT["deferred_requested_qty"], 9)
        self.assertEqual(c1.REPORT["by_item"]["WOOL"], 1)

    def test_multi_shop_demand_can_defer_multiple_flush_items(self):
        parent = action(market=[["SELL", "WOOL", 9], ["SELL", "MILK", 3], ["SELL", "STRAWBERRY", 2]])
        observation = obs(shops=["YARN_STORE", "PIZZA_SHOP", "BRUNCH_SPOT"])
        result = self.apply(observation, parent)
        self.assertEqual(result["market"], [[], [], []])
        self.assertEqual(c1.REPORT["deferred_rows"], 3)

    def test_melon_is_not_in_unlocked_shop_demand(self):
        parent = action(market=[["SELL", "MELON", 7]])
        observation = obs(shops=["YARN_STORE", "SMOOTHIE_SHOP", "FARMERS_MARKET"])
        self.assertIs(self.apply(observation, parent), parent)

    def test_only_hour20_after_day0_is_eligible(self):
        parent = action()
        for step in (20, 307, 309, 716, 718):
            with self.subTest(step=step):
                self.assertIs(self.apply(obs(step=step), parent), parent)

    def test_mixed_market_rows_fail_closed(self):
        parent = action(market=[["SELL", "WOOL", 9], ["BUY_PRODUCT", "WHEAT", 2]])
        self.assertIs(self.apply(obs(), parent), parent)

    def test_non_native_or_quantity_mutated_market_fails_closed(self):
        parent = action(market=[["SELL", "WOOL", 9], ["SELL", "MILK", 3]])
        native = [["SELL", "WOOL", 9]]
        self.assertIs(self.apply(obs(), parent, native=native), parent)
        parent2 = action(market=[["SELL", "WOOL", 8]])
        native2 = [["SELL", "WOOL", 9]]
        self.assertIs(self.apply(obs(), parent2, native=native2), parent2)

    def test_native_sell_reordering_is_allowed_but_indices_stay_current(self):
        parent = action(market=[["SELL", "MILK", 3], ["SELL", "WOOL", 9]])
        native = [["SELL", "WOOL", 9], ["SELL", "MILK", 3]]
        result = self.apply(obs(), parent, native=native)
        self.assertEqual(result["market"], [["SELL", "MILK", 3], []])

    def test_parent_sale_accounting_ownership_vetoes_item(self):
        parent = action()
        for state in (
            SaleState(advanced={"WOOL": 9}),
            SaleState(debts={309: {"WOOL": 9}}),
            SaleState(debts={316: {"WOOL": 4}}),
        ):
            with self.subTest(state=state.__dict__):
                self.assertIs(self.apply(obs(), parent, state=state), parent)

    def test_malformed_sale_accounting_fails_closed(self):
        parent = action()
        for state in (
            SaleState(advanced={"WOOL": True}),
            SaleState(debts={309.0: {"WOOL": 1}}),
            SaleState(debts={309: {"WOOL": "1"}}),
        ):
            with self.subTest(state=state.__dict__):
                self.assertIs(self.apply(obs(), parent, state=state), parent)

    def test_inventory_producers_veto_deferral(self):
        parent_harvest = action(farmer=["HARVEST"])
        self.assertIs(self.apply(obs(), parent_harvest), parent_harvest)
        parent_fert = action(farmer=["COLLECT_FERTILIZER"])
        self.assertIs(self.apply(obs(), parent_fert), parent_fert)
        hand_fert = action(hands=[["COLLECT_FERTILIZER"]])
        self.assertIs(self.apply(obs(inventories=[{}, {}]), hand_fert), hand_fert)

    def test_capacity_guard_counts_all_shed_and_carried_stock(self):
        parent = action()
        exactly_full = obs(shed={"WOOL": 90, "SHEEP": 5}, inventories=[{"WHEAT": 5}])
        self.assertEqual(self.apply(exactly_full, parent)["market"], [[]])
        overflow = obs(shed={"WOOL": 90, "SHEEP": 5}, inventories=[{"WHEAT": 6}])
        self.assertIs(self.apply(overflow, parent), parent)

    def test_pickup_drop_style_commands_do_not_create_total_stock(self):
        parent = action(farmer=["PICKUP", "WHEAT", 1])
        self.assertEqual(self.apply(obs(), parent)["market"], [[]])

    def test_bad_quantity_types_fail_closed(self):
        for market in (
            [["SELL", "WOOL", True]],
            [["SELL", "WOOL", 9.0]],
            [["SELL", "WOOL", "9"]],
            [["SELL", "WOOL"]],
            ["not-a-row"],
        ):
            with self.subTest(market=market):
                parent = action(market=market)
                self.assertIs(self.apply(obs(), parent), parent)

    def test_bad_observation_types_fail_closed(self):
        parent = action()
        for bad_step in (True, 308.0, "308", None):
            with self.subTest(step=bad_step):
                self.assertIs(self.apply(obs(step=bad_step), parent), parent)
        for bad_player in (True, 0.0, "0", -1, 2):
            with self.subTest(player=bad_player):
                self.assertIs(self.apply(obs(player=bad_player), parent), parent)
        bad = obs()
        bad["farms"] = [{"money": 0}]
        self.assertIs(self.apply(bad, parent), parent)

    def test_bad_private_stock_types_fail_closed(self):
        parent = action()
        for bad_shed in ({"WOOL": True}, {"WOOL": 9.0}, {"WOOL": -1}, None):
            with self.subTest(shed=bad_shed):
                self.assertIs(self.apply(obs(shed=bad_shed), parent), parent)
        for bad_inventories in (None, [], [{"WHEAT": "1"}], [None]):
            with self.subTest(inventories=bad_inventories):
                self.assertIs(self.apply(obs(inventories=bad_inventories), parent), parent)

    def test_unknown_or_malformed_shop_state_fails_closed(self):
        parent = action()
        for shops in (["NOT_A_SHOP"], [None], "YARN_STORE", None):
            with self.subTest(shops=shops):
                self.assertIs(self.apply(obs(shops=shops), parent), parent)

    def test_nonstandard_configuration_fails_closed(self):
        parent = action()
        bad_configs = (
            {"turnsPerDay": True},
            {"turnsPerDay": 12},
            {"townShopSellInterval": 5},
            {"shedCapacity": 100.0},
            {"episodeSteps": 719},
            {"marketParams": []},
            {"marketParams": {"WOOL": {"base": 999}}},
        )
        for configuration in bad_configs:
            with self.subTest(configuration=configuration):
                self.assertIs(self.apply(obs(), parent, configuration=configuration), parent)

    def test_malformed_action_carrier_fails_closed(self):
        observation = obs()
        cases = (
            {"farmer": None, "hands": [], "market": [["SELL", "WOOL", 9]]},
            {"farmer": ["PASS"], "hands": None, "market": [["SELL", "WOOL", 9]]},
            {"farmer": ["PASS"], "hands": [None], "market": [["SELL", "WOOL", 9]]},
            {"hands": [], "market": [["SELL", "WOOL", 9]]},
        )
        for parent in cases:
            with self.subTest(parent=parent):
                self.assertIs(
                    c1.apply_intertemporal_deferral(
                        observation,
                        parent,
                        native_market=[["SELL", "WOOL", 9]],
                    ),
                    parent,
                )

    def test_live_baseline_is_explicit(self):
        self.assertEqual(c1.LIVE_BASELINE, {
            "horizon": 8,
            "opening": 0,
            "row_order": True,
            "evening_flush": True,
            "sale_fertilizer": True,
            "cattle_early": True,
        })


if __name__ == "__main__":
    unittest.main()
