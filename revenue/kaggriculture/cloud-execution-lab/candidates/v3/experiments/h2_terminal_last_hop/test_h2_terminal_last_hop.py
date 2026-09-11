# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
OVERLAY = V3 / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_full_router as base  # noqa: E402
import r04_h2_terminal_last_hop as h2  # noqa: E402


STANDARD_CONFIG = {
    "boardSize": 10,
    "turnsPerDay": 24,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
}


def observation(
    *,
    step=717,
    player=0,
    farmer=(4, 3),
    hands=(),
    inventories=None,
    shed=None,
):
    size = 10
    tiles = [[None for _ in range(size)] for _ in range(size)]
    farm = {
        "tiles": tiles,
        "farmer": list(farmer),
        "hands": [list(position) for position in hands],
        "money": 1000,
        "unlocked_quadrants": ["NW", "NE", "SW", "SE"],
        "hires_today": 0,
    }
    if inventories is None:
        inventories = [{"MILK": 3}] + [{} for _ in hands]
    private = {
        "inventories": [dict(inventory) for inventory in inventories],
        "shed": dict(shed or {}),
    }
    prices = {item: 10 for item in base.PRODUCTS}
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": player,
        "farms": [copy.deepcopy(farm), copy.deepcopy(farm)],
        "private": private,
        "market": {"prices": prices, "inventory": {}},
        "town": {"unlocked_shops": []},
    }


def action(farmer=("PASS",), hands=(), market=None):
    if market is None:
        market = [["SELL", "WOOL", 2]]
    return {
        "farmer": list(farmer),
        "hands": [list(command) for command in hands],
        "market": copy.deepcopy(market),
    }


class H2TerminalLastHopTests(unittest.TestCase):
    def test_disabled_is_exact_parent_identity(self):
        act = action(("HARVEST",))
        out, actor, units = h2.rescue_last_hop(
            act, object(), object(), enabled=False
        )
        self.assertIs(out, act)
        self.assertEqual((actor, units), (None, 0))

    def test_exact_step717_pass_one_hop_rescues_product_cargo(self):
        act = action()
        obs = observation(farmer=(4, 3), inventories=[{"MILK": 3}])
        out, actor, units = h2.rescue_last_hop(
            act, obs, STANDARD_CONFIG, enabled=True
        )
        target = (4, 4)
        self.assertEqual(out["farmer"], base._v219_walk((4, 3), target))
        self.assertEqual((actor, units), (0, 3))
        self.assertEqual(out["market"], act["market"])
        self.assertEqual(act["farmer"], ["PASS"])

    def test_only_step717_is_owned(self):
        for step in (696, 716, 718):
            with self.subTest(step=step):
                act = action()
                obs = observation(step=step)
                out, actor, units = h2.rescue_last_hop(
                    act, obs, STANDARD_CONFIG, enabled=True
                )
                self.assertIs(out, act)
                self.assertEqual((actor, units), (None, 0))

    def test_parent_harvest_care_and_water_are_never_preempted(self):
        for command in (("HARVEST",), ("CARE",), ("WATER",)):
            with self.subTest(command=command):
                act = action(command)
                obs = observation()
                out, actor, units = h2.rescue_last_hop(
                    act, obs, STANDARD_CONFIG, enabled=True
                )
                self.assertIs(out, act)
                self.assertEqual((actor, units), (None, 0))

    def test_two_hops_away_is_not_touched(self):
        act = action()
        obs = observation(farmer=(4, 2))
        out, actor, units = h2.rescue_last_hop(
            act, obs, STANDARD_CONFIG, enabled=True
        )
        self.assertIs(out, act)
        self.assertEqual((actor, units), (None, 0))

    def test_already_beside_shed_is_parent_liquidation_safe(self):
        act = action()
        obs = observation(farmer=(4, 4), inventories=[{"WOOL": 5}])
        out, actor, units = h2.rescue_last_hop(
            act, obs, STANDARD_CONFIG, enabled=True
        )
        self.assertIs(out, act)
        self.assertEqual((actor, units), (None, 0))

    def test_occupied_last_hop_cell_fails_closed(self):
        act = action(hands=(("CARE",),))
        obs = observation(
            farmer=(4, 3),
            hands=((4, 4),),
            inventories=[{"MILK": 3}, {}],
        )
        out, actor, units = h2.rescue_last_hop(
            act, obs, STANDARD_CONFIG, enabled=True
        )
        self.assertIs(out, act)
        self.assertEqual((actor, units), (None, 0))

    def test_any_other_worker_move_fails_closed(self):
        act = action(hands=(("MOVE", "N"),))
        obs = observation(
            farmer=(4, 3), hands=((0, 0),), inventories=[{"MILK": 3}, {}]
        )
        out, actor, units = h2.rescue_last_hop(
            act, obs, STANDARD_CONFIG, enabled=True
        )
        self.assertIs(out, act)
        self.assertEqual((actor, units), (None, 0))

    def test_other_worker_product_creation_fails_closed(self):
        for command in (("HARVEST",), ("COLLECT_FERTILIZER",)):
            with self.subTest(command=command):
                act = action(hands=(command,))
                obs = observation(
                    farmer=(4, 3), hands=((0, 0),), inventories=[{"MILK": 3}, {}]
                )
                out, actor, units = h2.rescue_last_hop(
                    act, obs, STANDARD_CONFIG, enabled=True
                )
                self.assertIs(out, act)
                self.assertEqual((actor, units), (None, 0))

    def test_market_acquisition_or_malformed_row_fails_closed(self):
        markets = (
            [["BUY_PRODUCT", "WHEAT", 1]],
            [["HIRE"]],
            [["SELL", "WOOL", True]],
        )
        for market in markets:
            with self.subTest(market=market):
                act = action(market=market)
                obs = observation()
                out, actor, units = h2.rescue_last_hop(
                    act, obs, STANDARD_CONFIG, enabled=True
                )
                self.assertIs(out, act)
                self.assertEqual((actor, units), (None, 0))

    def test_whole_farm_capacity_bound_prevents_terminal_drop_overflow(self):
        act = action()
        obs = observation(inventories=[{"MILK": 3}], shed={"WOOL": 98})
        out, actor, units = h2.rescue_last_hop(
            act, obs, STANDARD_CONFIG, enabled=True
        )
        self.assertIs(out, act)
        self.assertEqual((actor, units), (None, 0))

    def test_positive_nonproduct_or_poisoned_cargo_fails_closed(self):
        bad = ({"COW": 1}, {"MILK": True}, {"MILK": -1})
        for inventory in bad:
            with self.subTest(inventory=inventory):
                act = action()
                obs = observation(inventories=[inventory])
                out, actor, units = h2.rescue_last_hop(
                    act, obs, STANDARD_CONFIG, enabled=True
                )
                self.assertIs(out, act)
                self.assertEqual((actor, units), (None, 0))

    def test_missing_nonstandard_or_bool_configuration_fails_closed(self):
        configs = (
            None,
            {},
            {**STANDARD_CONFIG, "boardSize": True},
            {**STANDARD_CONFIG, "shedCapacity": 101},
        )
        for config in configs:
            with self.subTest(config=config):
                act = action()
                obs = observation()
                out, actor, units = h2.rescue_last_hop(
                    act, obs, config, enabled=True
                )
                self.assertIs(out, act)
                self.assertEqual((actor, units), (None, 0))

    def test_malformed_player_positions_and_action_shapes_fail_closed(self):
        cases = []
        obs = observation()
        obs["player"] = True
        cases.append((action(), obs))
        obs = observation()
        obs["farms"][0]["farmer"] = [4, 3, 99]
        cases.append((action(), obs))
        obs = observation(hands=((0, 0),), inventories=[{"MILK": 3}, {}])
        cases.append((action(hands=()), obs))
        for act, obs in cases:
            with self.subTest(obs=obs):
                out, actor, units = h2.rescue_last_hop(
                    act, obs, STANDARD_CONFIG, enabled=True
                )
                self.assertIs(out, act)
                self.assertEqual((actor, units), (None, 0))

    def test_hand_can_be_the_single_rescued_actor(self):
        act = action(("CARE",), hands=(("PASS",),))
        obs = observation(
            farmer=(0, 0),
            hands=((4, 3),),
            inventories=[{}, {"STRAWBERRY": 4}],
        )
        out, actor, units = h2.rescue_last_hop(
            act, obs, STANDARD_CONFIG, enabled=True
        )
        self.assertEqual(out["farmer"], ["CARE"])
        self.assertEqual(out["hands"][0], base._v219_walk((4, 3), (4, 4)))
        self.assertEqual((actor, units), (1, 4))
        self.assertEqual(out["market"], act["market"])

    def test_multiple_eligible_workers_rescue_only_lowest_actor(self):
        act = action(hands=(("PASS",),))
        obs = observation(
            farmer=(4, 3),
            hands=((5, 3),),
            inventories=[{"MILK": 1}, {"WOOL": 2}],
        )
        out, actor, units = h2.rescue_last_hop(
            act, obs, STANDARD_CONFIG, enabled=True
        )
        self.assertEqual((actor, units), (0, 1))
        self.assertNotEqual(out["farmer"], ["PASS"])
        self.assertEqual(out["hands"][0], ["PASS"])

    def test_install_off_preserves_exact_parent_object_and_enabled_type_is_strict(self):
        parent_action = action()
        parent = lambda observation, configuration=None: parent_action
        wrapped = h2.install(parent, enabled=False)
        self.assertIs(wrapped(observation(), STANDARD_CONFIG), parent_action)
        with self.assertRaises(TypeError):
            h2.install(parent, enabled=1)
        with self.assertRaises(TypeError):
            h2.rescue_last_hop(parent_action, observation(), STANDARD_CONFIG, enabled=1)


if __name__ == "__main__":
    unittest.main()
