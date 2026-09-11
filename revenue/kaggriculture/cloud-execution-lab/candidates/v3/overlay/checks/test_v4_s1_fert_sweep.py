# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 S1 fertilizer-sweep hand."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_s1_fert_sweep as lane  # noqa: E402
import r04_full_router as r04  # noqa: E402
from titan_runtime import Features  # noqa: E402


CONFIG = {
    "episodeSteps": 720,
    "turnsPerDay": 24,
    "boardSize": 10,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
    "farmHandCostMult": 1,
}


def animal(kind="GOOSE", *, fertilizer=True):
    return {
        "kind": "COOP" if kind == "GOOSE" else "PASTURE",
        "animal": kind,
        "fertilizer_available": fertilizer,
        "fed_today": True,
        "cared_today": True,
        "yield_units": 0,
    }


def pass_tape():
    return [
        {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}
        for _ in range(720)
    ]


def observation(*, step=4 * 24 + 14, hires_today=2, money=5000.0,
                fertilizer_price=100, targets=((4, 3), (3, 4), (4, 2)),
                hands=None, inventories=None, shed=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    for x, y in targets:
        tiles[y][x] = animal()
    farm = {
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": copy.deepcopy(hands if hands is not None else [[4, 4]]),
        "money": money,
        "unlocked_quadrants": ["NW", "NE", "SW"],
        "hires_today": hires_today,
    }
    private_inventories = copy.deepcopy(
        inventories if inventories is not None else [{}, {}]
    )
    private = {
        "inventories": private_inventories,
        "shed": copy.deepcopy(shed if shed is not None else {"FERTILIZER": 0}),
        "seeds": {},
    }
    prices = {
        "WHEAT": 25,
        "CARROT": 35,
        "TOMATO": 80,
        "STRAWBERRY": 120,
        "MELON": 80,
        "EGG": 100,
        "MILK": 100,
        "WOOL": 100,
        "FERTILIZER": fertilizer_price,
    }
    other = copy.deepcopy(farm)
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [farm, other],
        "private": private,
        "market": {"prices": prices},
        "town": {"unlocked_shops": []},
    }


def action(*, market=None, farmer=None, hands=None):
    return {
        "farmer": copy.deepcopy(farmer if farmer is not None else ["PASS"]),
        "hands": copy.deepcopy(hands if hands is not None else [["PASS"]]),
        "market": copy.deepcopy(market if market is not None else []),
    }


class S1FertSweepTest(unittest.TestCase):
    def setUp(self):
        lane._STATE.clear()
        for key in lane.REPORT:
            lane.REPORT[key] = 0

    def test_standard_configuration_is_exact(self):
        self.assertTrue(lane.standard_configuration(CONFIG))
        bad = [
            None,
            {**CONFIG, "episodeSteps": 719},
            {**CONFIG, "turnsPerDay": 23},
            {**CONFIG, "boardSize": 9},
            {**CONFIG, "shedCapacity": 99},
            {**CONFIG, "maxMarketOrdersPerTurn": 9},
            {**CONFIG, "farmHandCostMult": 2},
            {**CONFIG, "farmHandCostMult": True},
            {**CONFIG, "episodeSteps": True},
            {**CONFIG, "marketParams": {"WHEAT": {}}},
            {**CONFIG, "marketParams": []},
        ]
        for cfg in bad:
            with self.subTest(cfg=cfg):
                self.assertFalse(lane.standard_configuration(cfg))

    def test_reachable_count_uses_worst_case_route_budget(self):
        targets = [(4, 3), (3, 4), (4, 2)]
        starts = lane._shed_tiles(10)
        counts = [lane._reachable_count(start, targets, 9) for start in starts]
        self.assertGreaterEqual(min(counts), 2)

    def test_eligible_parent_gets_one_appended_hire(self):
        obs = observation()
        st = lane._Day(4)
        result = lane._consider_hire(obs, action(), st, pass_tape(), CONFIG)
        self.assertEqual(result["market"], [["HIRE"]])
        self.assertEqual(st.pending, 1)
        self.assertTrue(st.tried)

    def test_sell_rows_can_precede_hire_but_buy_rows_cannot(self):
        obs = observation()
        st = lane._Day(4)
        sold = action(market=[["SELL", "CARROT", 1]])
        result = lane._consider_hire(obs, sold, st, pass_tape(), CONFIG)
        self.assertEqual(result["market"], [["SELL", "CARROT", 1], ["HIRE"]])

        st = lane._Day(4)
        bought = action(market=[["BUY_SEED", "WHEAT", 1]])
        self.assertIs(lane._consider_hire(obs, bought, st, pass_tape(), CONFIG), bought)

    def test_current_collect_blocks_hire(self):
        obs = observation()
        st = lane._Day(4)
        parent = action(farmer=["COLLECT_FERTILIZER"])
        self.assertIs(lane._consider_hire(obs, parent, st, pass_tape(), CONFIG), parent)

    def test_future_native_hire_blocks_hire(self):
        obs = observation()
        tape = pass_tape()
        tape[obs["step"] + 2]["market"] = [["HIRE"]]
        st = lane._Day(4)
        parent = action()
        self.assertIs(lane._consider_hire(obs, parent, st, tape, CONFIG), parent)

    def test_future_native_purchase_and_unknown_market_rows_block_hire(self):
        obs = observation()
        for order in (
            ["BUY_LAND", "NE"],
            ["BUY_PRODUCT", "WHEAT", 1],
            ["BUY_SEED", "WHEAT", 1],
            ["BUY_ANIMAL", "SHEEP", 1],
            ["UNKNOWN_MARKET_OP"],
        ):
            with self.subTest(order=order):
                tape = pass_tape()
                tape[obs["step"] + 2]["market"] = [order]
                st = lane._Day(4)
                parent = action()
                self.assertIs(
                    lane._consider_hire(obs, parent, st, tape, CONFIG),
                    parent,
                )

    def test_future_native_sell_does_not_block_hire(self):
        obs = observation()
        tape = pass_tape()
        tape[obs["step"] + 2]["market"] = [["SELL", "WHEAT", 1]]
        st = lane._Day(4)
        result = lane._consider_hire(obs, action(), st, tape, CONFIG)
        self.assertEqual(result["market"], [["HIRE"]])

    def test_future_native_collection_blocks_hire(self):
        obs = observation()
        tape = pass_tape()
        tape[obs["step"] + 2]["farmer"] = ["COLLECT_FERTILIZER"]
        st = lane._Day(4)
        parent = action()
        self.assertIs(lane._consider_hire(obs, parent, st, tape, CONFIG), parent)

    def test_se_v233_territory_is_not_owned_by_s1(self):
        obs = observation(targets=((5, 5), (6, 5), (7, 5), (5, 6)))
        st = lane._Day(4)
        parent = action()
        self.assertIs(lane._consider_hire(obs, parent, st, pass_tape(), CONFIG), parent)

    def test_late_unreachable_target_does_not_hire(self):
        obs = observation(step=4 * 24 + 22, targets=((0, 0),))
        st = lane._Day(4)
        parent = action()
        self.assertIs(lane._consider_hire(obs, parent, st, pass_tape(), CONFIG), parent)

    def test_value_gate_uses_fibonacci_hire_cost(self):
        obs = observation(hires_today=10, fertilizer_price=1)
        st = lane._Day(4)
        parent = action()
        self.assertIs(lane._consider_hire(obs, parent, st, pass_tape(), CONFIG), parent)
        self.assertEqual(lane.REPORT["value_declines"], 1)

    def test_capacity_headroom_blocks_speculative_collection(self):
        obs = observation(shed={"FERTILIZER": 87})
        st = lane._Day(4)
        parent = action()
        self.assertIs(lane._consider_hire(obs, parent, st, pass_tape(), CONFIG), parent)
        self.assertEqual(lane.REPORT["capacity_declines"], 1)

    def test_engine_float_money_is_valid_but_bool_nan_inf_fail_closed(self):
        parent = action()
        good = observation(money=5000.0)
        st = lane._Day(4)
        self.assertEqual(
            lane._consider_hire(good, parent, st, pass_tape(), CONFIG)["market"],
            [["HIRE"]],
        )
        for value in (True, float("nan"), float("inf"), -1.0):
            with self.subTest(value=value):
                obs = observation(money=value)
                st = lane._Day(4)
                parent = action()
                self.assertIs(
                    lane._consider_hire(obs, parent, st, pass_tape(), CONFIG),
                    parent,
                )

    def test_days_24_through_29_do_not_hire(self):
        for day in range(24, 30):
            with self.subTest(day=day):
                obs = observation(step=day * 24 + 14)
                st = lane._Day(day)
                parent = action()
                self.assertIs(
                    lane._consider_hire(obs, parent, st, pass_tape(), CONFIG),
                    parent,
                )

    def test_hidden_hand_is_removed_from_parent_and_reinserted_at_same_index(self):
        tape = pass_tape()
        seen = []

        def parent(obs, configuration=None):
            seen.append(
                (len(obs["farms"][0]["hands"]), len(obs["private"]["inventories"]))
            )
            return action(hands=[["PASS"]])

        wrapped = lane.wrap(parent, lambda obs: tape)
        first = observation()
        result = wrapped(first, CONFIG)
        self.assertEqual(result["market"], [["HIRE"]])

        second = observation(
            step=first["step"] + 1,
            hands=[[4, 4], [4, 3]],
            inventories=[{}, {}, {}],
        )
        result = wrapped(second, CONFIG)
        self.assertEqual(seen[-1], (1, 2))
        self.assertEqual(result["hands"], [["PASS"], ["COLLECT_FERTILIZER"]])
        self.assertEqual(lane.REPORT["hires"], 1)
        self.assertEqual(lane.REPORT["collections"], 1)

    def test_hidden_hand_walks_toward_nearest_reachable_target(self):
        tape = pass_tape()

        def parent(obs, configuration=None):
            return action(hands=[["PASS"]])

        wrapped = lane.wrap(parent, lambda obs: tape)
        first = observation(targets=((2, 4), (4, 2)))
        self.assertEqual(wrapped(first, CONFIG)["market"], [["HIRE"]])
        second = observation(
            step=first["step"] + 1,
            targets=((2, 4), (4, 2)),
            hands=[[4, 4], [4, 4]],
            inventories=[{}, {}, {}],
        )
        result = wrapped(second, CONFIG)
        self.assertIn(result["hands"][1], (["NORTH"], ["WEST"]))

    def test_malformed_actor_cardinality_fails_closed(self):
        obs = observation(inventories=[{}])
        sentinel = action()
        calls = []

        def parent(o, configuration=None):
            calls.append(o)
            return sentinel

        wrapped = lane.wrap(parent, lambda o: pass_tape())
        self.assertIs(wrapped(obs, CONFIG), sentinel)
        self.assertEqual(len(calls), 1)

    def test_generated_key_contract_defaults_off(self):
        self.assertFalse(Features().r04_s1_fert_sweep)
        self.assertFalse(r04.S1_FERT_SWEEP)
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_s1_fert_sweep"], False)

    def test_install_flag_round_trip(self):
        old = r04.S1_FERT_SWEEP
        try:
            r04.install(s1_fert_sweep=True)
            self.assertIs(r04.S1_FERT_SWEEP, True)
            r04.install(s1_fert_sweep=False)
            self.assertIs(r04.S1_FERT_SWEEP, False)
        finally:
            r04.S1_FERT_SWEEP = old


if __name__ == "__main__":
    unittest.main()
