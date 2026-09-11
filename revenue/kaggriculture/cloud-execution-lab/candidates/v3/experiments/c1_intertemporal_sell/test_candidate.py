from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("c1_candidate_tested", HERE / "candidate.py")
assert SPEC and SPEC.loader
c1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c1)


STANDARD_CONFIG = {
    "turnsPerDay": 24,
    "townShopSellInterval": 4,
    "shedCapacity": 100,
    "episodeSteps": 720,
    "maxMarketOrdersPerTurn": 10,
    "marketParams": {},
}


class SaleState:
    def __init__(self, *, advanced=None, debts=None, sale_due_step=-1):
        self.advanced_sales = {} if advanced is None else advanced
        self.sale_window_debts = {} if debts is None else debts
        self.sale_due_step = sale_due_step


_DEFAULT = object()


def obs(*, shops=_DEFAULT, shed=_DEFAULT, inventories=_DEFAULT, step=380, player=0):
    return {
        "step": step,  # day15 hour20, inside post-288 E184 regime
        "player": player,
        "town": {"unlocked_shops": ["BRUNCH_SPOT"] if shops is _DEFAULT else shops},
        "farms": [{"money": 0}, {"money": 0}],
        "private": {
            "shed": {"STRAWBERRY": 9, "MILK": 3, "WOOL": 4} if shed is _DEFAULT else shed,
            "inventories": [{}] if inventories is _DEFAULT else inventories,
        },
    }


def action(*, farmer=None, hands=None, market=None):
    return {
        "farmer": ["PASS"] if farmer is None else farmer,
        "hands": [] if hands is None else hands,
        "market": [["SELL", "STRAWBERRY", 9]] if market is None else market,
    }


class C1IntertemporalSellTests(unittest.TestCase):
    def setUp(self):
        c1.REPORT["callbacks"] = 0
        c1.REPORT["deferrals"] = 0
        c1.REPORT["deferred_rows"] = 0
        c1.REPORT["deferred_requested_qty"] = 0
        c1.REPORT["by_item"]["STRAWBERRY"] = 0

    def snap(self, state, step=380):
        return c1.snapshot_sale_provenance(state, step)

    def apply(
        self,
        observation,
        parent,
        *,
        native=None,
        pre_state=None,
        post_state=None,
        configuration=_DEFAULT,
    ):
        step = observation.get("step") if isinstance(observation, dict) else 380
        pre_state = SaleState() if pre_state is None else pre_state
        post_state = pre_state if post_state is None else post_state
        config = STANDARD_CONFIG if configuration is _DEFAULT else configuration
        return c1.apply_intertemporal_deferral(
            observation,
            parent,
            native_market=parent["market"] if native is None else native,
            pre_sale_snapshot=self.snap(pre_state, step),
            post_sale_snapshot=self.snap(post_state, step),
            configuration=config,
        )

    def test_brunch_spot_defers_proven_native_strawberry_in_same_market_slot(self):
        parent = action(market=[[], ["SELL", "STRAWBERRY", 9], ["SELL", "WOOL", 4]])
        result = self.apply(obs(), parent)
        self.assertIsNot(result, parent)
        self.assertEqual(result["market"], [[], [], ["SELL", "WOOL", 4]])
        self.assertEqual(parent["market"], [[], ["SELL", "STRAWBERRY", 9], ["SELL", "WOOL", 4]])
        self.assertEqual(c1.REPORT["deferrals"], 1)
        self.assertEqual(c1.REPORT["deferred_rows"], 1)
        self.assertEqual(c1.REPORT["deferred_requested_qty"], 9)
        self.assertEqual(c1.REPORT["by_item"]["STRAWBERRY"], 1)

    def test_multiple_native_strawberry_rows_keep_raw_indices(self):
        parent = action(market=[
            ["SELL", "STRAWBERRY", 2],
            ["SELL", "WOOL", 4],
            ["SELL", "STRAWBERRY", 3],
        ])
        result = self.apply(obs(), parent)
        self.assertEqual(result["market"], [[], ["SELL", "WOOL", 4], []])
        self.assertEqual(c1.REPORT["deferred_rows"], 2)

    def test_v233_wool_like_same_multiset_replacement_is_never_targeted(self):
        parent = action(market=[["SELL", "WOOL", 9]])
        observation = obs(shops=["YARN_STORE", "BRUNCH_SPOT"])
        # Even if final SELL multiset exactly matches a native WOOL tape row, C1 no longer
        # claims provenance for an item V233 can synthesize after spending wool credit.
        self.assertIs(self.apply(observation, parent), parent)

    def test_v231_milk_like_same_multiset_replacement_is_never_targeted(self):
        parent = action(market=[["SELL", "MILK", 3]])
        observation = obs(shops=["PIZZA_SHOP", "BRUNCH_SPOT"])
        # V231 can top up MILK quantity from milk_credit; MILK is outside the repaired theorem.
        self.assertIs(self.apply(observation, parent), parent)

    def test_current_due_e184_strawberry_debt_vetoes_native_looking_row(self):
        parent = action()
        pre = SaleState(debts={380: {"STRAWBERRY": 9}})
        post = SaleState()
        self.assertIs(self.apply(obs(), parent, pre_state=pre, post_state=post), parent)

    def test_legacy_advanced_strawberry_ownership_vetoes_row(self):
        parent = action()
        pre = SaleState(advanced={"STRAWBERRY": 9}, sale_due_step=380)
        post = SaleState()
        self.assertIs(self.apply(obs(), parent, pre_state=pre, post_state=post), parent)

    def test_same_callback_new_future_strawberry_debt_vetoes_e184_synthesis(self):
        parent = action()
        pre = SaleState(debts={382: {"WOOL": 2}})
        post = SaleState(debts={382: {"WOOL": 2}, 384: {"STRAWBERRY": 9}})
        self.assertIs(self.apply(obs(), parent, pre_state=pre, post_state=post), parent)

    def test_unchanged_future_strawberry_debt_is_not_current_ownership(self):
        parent = action()
        pre = SaleState(debts={384: {"STRAWBERRY": 2}})
        post = SaleState(debts={384: {"STRAWBERRY": 2}})
        self.assertEqual(self.apply(obs(), parent, pre_state=pre, post_state=post)["market"], [[]])

    def test_full_pre_and_post_accounting_schema_is_fail_closed(self):
        parent = action()
        bad_states = (
            SaleState(advanced={"STRAWBERRY": True}),
            SaleState(advanced={"NOT_A_PRODUCT": 1}),
            SaleState(debts={380.0: {"STRAWBERRY": 1}}),
            SaleState(debts={380: {"STRAWBERRY": "1"}}),
            SaleState(debts={380: {"NOT_A_PRODUCT": 1}}),
            SaleState(debts={720: {"STRAWBERRY": 1}}),
            SaleState(sale_due_step=True),
        )
        for state in bad_states:
            with self.subTest(state=state.__dict__):
                self.assertIs(self.apply(obs(), parent, pre_state=state), parent)

    def test_only_post_advance_hour20_is_eligible(self):
        parent = action()
        for step in (20, 284, 307, 309, 716, 718):
            with self.subTest(step=step):
                self.assertIs(self.apply(obs(step=step), parent), parent)
        self.assertEqual(self.apply(obs(step=308), parent)["market"], [[]])

    def test_mixed_market_rows_fail_closed(self):
        parent = action(market=[["SELL", "STRAWBERRY", 9], ["BUY_PRODUCT", "WHEAT", 2]])
        self.assertIs(self.apply(obs(), parent), parent)

    def test_non_native_or_quantity_mutated_market_fails_closed(self):
        parent = action(market=[["SELL", "STRAWBERRY", 9], ["SELL", "WOOL", 4]])
        native = [["SELL", "STRAWBERRY", 9]]
        self.assertIs(self.apply(obs(), parent, native=native), parent)
        parent2 = action(market=[["SELL", "STRAWBERRY", 8]])
        native2 = [["SELL", "STRAWBERRY", 9]]
        self.assertIs(self.apply(obs(), parent2, native=native2), parent2)

    def test_native_sell_reordering_is_allowed_but_indices_stay_current(self):
        parent = action(market=[["SELL", "WOOL", 4], ["SELL", "STRAWBERRY", 9]])
        native = [["SELL", "STRAWBERRY", 9], ["SELL", "WOOL", 4]]
        result = self.apply(obs(), parent, native=native)
        self.assertEqual(result["market"], [["SELL", "WOOL", 4], []])

    def test_inventory_producers_veto_deferral(self):
        parent_harvest = action(farmer=["HARVEST"])
        self.assertIs(self.apply(obs(), parent_harvest), parent_harvest)
        parent_fert = action(farmer=["COLLECT_FERTILIZER"])
        self.assertIs(self.apply(obs(), parent_fert), parent_fert)
        hand_fert = action(hands=[["COLLECT_FERTILIZER"]])
        self.assertIs(self.apply(obs(inventories=[{}, {}]), hand_fert), hand_fert)

    def test_inventory_cardinality_must_match_farmer_plus_hands(self):
        parent = action(hands=[["PASS"]])
        malformed = obs(inventories=[{}])
        self.assertIs(self.apply(malformed, parent), parent)
        valid = obs(inventories=[{}, {}])
        self.assertEqual(self.apply(valid, parent)["market"], [[]])

    def test_capacity_guard_counts_all_shed_and_carried_stock(self):
        parent = action()
        exactly_full = obs(shed={"STRAWBERRY": 90, "SHEEP": 5}, inventories=[{"WHEAT": 5}])
        self.assertEqual(self.apply(exactly_full, parent)["market"], [[]])
        overflow = obs(shed={"STRAWBERRY": 90, "SHEEP": 5}, inventories=[{"WHEAT": 6}])
        self.assertIs(self.apply(overflow, parent), parent)

    def test_pickup_drop_style_commands_do_not_create_total_stock(self):
        parent = action(farmer=["PICKUP", "WHEAT", 1])
        self.assertEqual(self.apply(obs(), parent)["market"], [[]])

    def test_bool_float_string_and_short_sell_quantities_fail_closed(self):
        for market in (
            [["SELL", "STRAWBERRY", True]],
            [["SELL", "STRAWBERRY", 9.0]],
            [["SELL", "STRAWBERRY", "9"]],
            [["SELL", "STRAWBERRY"]],
            ["not-a-row"],
        ):
            with self.subTest(market=market):
                parent = action(market=market)
                self.assertIs(self.apply(obs(), parent), parent)

    def test_bad_observation_types_fail_closed(self):
        parent = action()
        for bad_step in (True, 380.0, "380", None):
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
        for bad_shed in ({"STRAWBERRY": True}, {"STRAWBERRY": 9.0}, {"STRAWBERRY": -1}, None):
            with self.subTest(shed=bad_shed):
                self.assertIs(self.apply(obs(shed=bad_shed), parent), parent)
        for bad_inventories in (None, [], [{"WHEAT": "1"}], [None]):
            with self.subTest(inventories=bad_inventories):
                self.assertIs(self.apply(obs(inventories=bad_inventories), parent), parent)

    def test_unknown_or_malformed_shop_state_fails_closed(self):
        parent = action()
        for shops in (["NOT_A_SHOP"], [None], "BRUNCH_SPOT", None):
            with self.subTest(shops=shops):
                self.assertIs(self.apply(obs(shops=shops), parent), parent)

    def test_none_empty_and_partial_configuration_fail_closed(self):
        parent = action()
        bad_configs = (
            None,
            {},
            {"turnsPerDay": 24},
            {**STANDARD_CONFIG, "turnsPerDay": True},
            {**STANDARD_CONFIG, "townShopSellInterval": 5},
            {**STANDARD_CONFIG, "shedCapacity": 100.0},
            {**STANDARD_CONFIG, "episodeSteps": 719},
            {**STANDARD_CONFIG, "maxMarketOrdersPerTurn": 9},
            {**STANDARD_CONFIG, "marketParams": []},
            {**STANDARD_CONFIG, "marketParams": {"WOOL": {"base": 999}}},
        )
        for configuration in bad_configs:
            with self.subTest(configuration=configuration):
                self.assertIs(self.apply(obs(), parent, configuration=configuration), parent)

    def test_complete_standard_configuration_is_required_and_sufficient(self):
        parent = action()
        self.assertEqual(self.apply(obs(), parent, configuration=dict(STANDARD_CONFIG))["market"], [[]])

    def test_malformed_action_carrier_fails_closed(self):
        observation = obs()
        cases = (
            {"farmer": None, "hands": [], "market": [["SELL", "STRAWBERRY", 9]]},
            {"farmer": ["PASS"], "hands": None, "market": [["SELL", "STRAWBERRY", 9]]},
            {"farmer": ["PASS"], "hands": [None], "market": [["SELL", "STRAWBERRY", 9]]},
            {"hands": [], "market": [["SELL", "STRAWBERRY", 9]]},
        )
        for parent in cases:
            with self.subTest(parent=parent):
                pre = self.snap(SaleState())
                self.assertIs(
                    c1.apply_intertemporal_deferral(
                        observation,
                        parent,
                        native_market=[["SELL", "STRAWBERRY", 9]],
                        pre_sale_snapshot=pre,
                        post_sale_snapshot=pre,
                        configuration=STANDARD_CONFIG,
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
