#!/usr/bin/env python3
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import candidate as b9  # noqa: E402


def observation(step=717, *, farmer=(3, 4), hands=None, inventories=None, shed=None):
    hands = list(hands or [])
    positions = [list(farmer), *[list(pos) for pos in hands]]
    if inventories is None:
        inventories = [{"WHEAT": 3}] + [{} for _ in hands]
    farm = {
        "farmer": positions[0],
        "hands": positions[1:],
        "tiles": [[None for _ in range(10)] for _ in range(10)],
    }
    return {
        "step": step,
        "player": 0,
        "farms": [farm],
        "private": {
            "inventories": copy.deepcopy(inventories),
            "shed": copy.deepcopy(shed or {}),
        },
        "market": {"prices": {item: 10 for item in b9.base.PRODUCTS}},
        "town": {"unlocked_shops": []},
    }


def action(*, farmer=None, hands=None, market=None):
    return {
        "farmer": list(farmer or ["PASS"]),
        "hands": copy.deepcopy(hands or []),
        "market": copy.deepcopy(market or []),
    }


class B9TerminalOneHopReturnTests(unittest.TestCase):
    def setUp(self):
        b9.telemetry.clear()

    def test_disabled_exact_identity(self):
        parent = action(market=[["SELL", "MILK", 2]])
        out = b9.terminal_onehop_return(parent, observation(), enabled=False)
        self.assertIs(out, parent)
        self.assertEqual(parent["market"], [["SELL", "MILK", 2]])

    def test_only_step_717_is_eligible(self):
        for step in (716, 718):
            with self.subTest(step=step):
                parent = action()
                self.assertIs(
                    b9.terminal_onehop_return(parent, observation(step=step), enabled=True),
                    parent,
                )

    def test_farmer_one_hop_pass_moves_home_and_preserves_market(self):
        parent = action(market=[["SELL", "MILK", 2], [], ["BUY_SEED", "WHEAT", 1]])
        original = copy.deepcopy(parent)
        out = b9.terminal_onehop_return(parent, observation(), enabled=True)
        self.assertEqual(out["farmer"], ["EAST"])
        self.assertEqual(out["hands"], [])
        self.assertEqual(out["market"], original["market"])
        self.assertEqual(parent, original)
        self.assertEqual(b9.telemetry["workers_returned"], 1)
        self.assertEqual(b9.telemetry["cargo_units_returned"], 3)

    def test_hand_can_return_while_farmer_is_untouched(self):
        obs = observation(
            farmer=(0, 0),
            hands=[(6, 5)],
            inventories=[{}, {"MILK": 2}],
        )
        parent = action(farmer=["WATER"], hands=[["PASS"]])
        out = b9.terminal_onehop_return(parent, obs, enabled=True)
        self.assertEqual(out["farmer"], ["WATER"])
        self.assertEqual(out["hands"], [["WEST"]])

    def test_non_pass_worker_is_never_stolen(self):
        parent = action(farmer=["HARVEST"])
        self.assertIs(b9.terminal_onehop_return(parent, observation(), enabled=True), parent)

    def test_distance_two_is_not_generalized(self):
        parent = action()
        obs = observation(farmer=(2, 4))
        self.assertIs(b9.terminal_onehop_return(parent, obs, enabled=True), parent)

    def test_already_home_is_not_rewritten(self):
        parent = action()
        obs = observation(farmer=(4, 4))
        self.assertIs(b9.terminal_onehop_return(parent, obs, enabled=True), parent)

    def test_positive_non_product_cargo_makes_actor_ineligible(self):
        parent = action()
        obs = observation(inventories=[{"WHEAT": 3, "SHEEP": 1}])
        self.assertIs(b9.terminal_onehop_return(parent, obs, enabled=True), parent)

    def test_malformed_inventory_fails_closed(self):
        bad_values = (True, 1.0, "1", -1)
        for bad in bad_values:
            with self.subTest(bad=bad):
                parent = action()
                obs = observation(inventories=[{"WHEAT": bad}])
                self.assertIs(b9.terminal_onehop_return(parent, obs, enabled=True), parent)

    def test_malformed_position_and_type_loose_config_fail_closed(self):
        parent = action()
        malformed = observation()
        malformed["farms"][0]["farmer"] = [3.0, 4]
        self.assertIs(b9.terminal_onehop_return(parent, malformed, enabled=True), parent)

        for config in (
            {"boardSize": True},
            {"turnsPerDay": 24.0},
            {"shedCapacity": "100"},
            {"maxMarketOrdersPerTurn": 10.0},
        ):
            with self.subTest(config=config):
                candidate_parent = action()
                self.assertIs(
                    b9.terminal_onehop_return(candidate_parent, observation(), config, enabled=True),
                    candidate_parent,
                )

    def test_capacity_boundary_is_conservative(self):
        parent = action()
        pass_obs = observation(shed={"MILK": 97})
        pass_out = b9.terminal_onehop_return(parent, pass_obs, enabled=True)
        self.assertEqual(pass_out["farmer"], ["EAST"])

        blocked_parent = action()
        blocked_obs = observation(shed={"MILK": 98})
        self.assertIs(
            b9.terminal_onehop_return(blocked_parent, blocked_obs, enabled=True),
            blocked_parent,
        )
        self.assertEqual(b9.telemetry["capacity_block"], 1)

    def test_same_turn_other_worker_drop_consumes_room_before_terminal(self):
        # Actor0 is the B9 candidate one step from home. Actor1 is already home and its parent
        # DROP consumes two units of the currently-empty room before the final-turn liquidation.
        obs = observation(
            farmer=(3, 4),
            hands=[(4, 4)],
            inventories=[{"WHEAT": 3}, {"MILK": 2}],
            shed={"CARROT": 96},
        )
        parent = action(hands=[["DROP"]])
        self.assertIs(b9.terminal_onehop_return(parent, obs, enabled=True), parent)
        self.assertEqual(b9.telemetry["capacity_block"], 1)

    def test_multiple_eligible_workers_are_all_or_nothing_on_capacity(self):
        obs = observation(
            farmer=(3, 4),
            hands=[(6, 5)],
            inventories=[{"WHEAT": 2}, {"MILK": 3}],
            shed={"CARROT": 95},
        )
        parent = action(hands=[["PASS"]])
        out = b9.terminal_onehop_return(parent, obs, enabled=True)
        self.assertEqual(out["farmer"], ["EAST"])
        self.assertEqual(out["hands"], [["WEST"]])

        blocked_parent = action(hands=[["PASS"]])
        blocked_obs = observation(
            farmer=(3, 4),
            hands=[(6, 5)],
            inventories=[{"WHEAT": 2}, {"MILK": 3}],
            shed={"CARROT": 96},
        )
        self.assertIs(
            b9.terminal_onehop_return(blocked_parent, blocked_obs, enabled=True),
            blocked_parent,
        )

    def test_step718_liquidate_drops_home_cargo_and_requests_sale(self):
        obs = observation(
            step=718,
            farmer=(4, 4),
            inventories=[{"WHEAT": 3}],
            shed={},
        )
        view = b9.base.FarmView(obs)
        final = b9.base.liquidate(view)
        self.assertEqual(final["farmer"], ["DROP"])
        self.assertIn(["SELL", "WHEAT", 3], final["market"])

    def test_market_rows_and_unrelated_commands_are_byte_semantically_preserved(self):
        parent = action(
            farmer=["PASS"],
            hands=[["WATER"]],
            market=[[], ["SELL", "MILK", 4], ["BUY_SEED", "WHEAT", 1]],
        )
        obs = observation(
            farmer=(3, 4),
            hands=[(0, 0)],
            inventories=[{"WHEAT": 1}, {}],
        )
        original = copy.deepcopy(parent)
        out = b9.terminal_onehop_return(parent, obs, enabled=True)
        self.assertEqual(out["market"], original["market"])
        self.assertEqual(out["hands"], original["hands"])
        self.assertEqual(parent, original)


if __name__ == "__main__":
    unittest.main()
