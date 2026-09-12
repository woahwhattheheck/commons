# SPDX-License-Identifier: Apache-2.0
"""Standalone S1 remaining-day, actor-index, and finite-value contracts."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_s1_fert_sweep as lane  # noqa: E402


CONFIG = {
    "episodeSteps": 720,
    "turnsPerDay": 24,
    "boardSize": 10,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
    "farmHandCostMult": 1,
}


def animal(kind="GOOSE", *, fertilizer=True, fed=True, consecutive_unfed=0):
    return {
        "kind": "COOP" if kind == "GOOSE" else "PASTURE",
        "animal": kind,
        "fertilizer_available": fertilizer,
        "fed_today": fed,
        "consecutive_unfed": consecutive_unfed,
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


class S1RemainingDayContractTest(unittest.TestCase):
    def setUp(self):
        lane._STATE.clear()
        for key in lane.REPORT:
            lane.REPORT[key] = 0


    def test_incomplete_remaining_day_tape_cannot_certify_no_obligations(self):
        obs = observation()
        end = (obs["step"] // 24 + 1) * 24
        for length in (0, obs["step"], obs["step"] + 1, end - 1):
            with self.subTest(length=length):
                parent = action()
                st = lane._Day(4)
                self.assertIs(lane._consider_hire(
                    obs, parent, st, pass_tape()[:length], CONFIG), parent)
                self.assertIsNone(st.pending)
                self.assertFalse(st.tried)
        result = lane._consider_hire(
            obs, action(), lane._Day(4), pass_tape()[:end], CONFIG)
        self.assertEqual(result["market"], [["HIRE"]])


    def test_wheat_obligations_cover_both_actors_and_last_eod_callback(self):
        obs = observation()
        end = (obs["step"] // 24 + 1) * 24
        for actor in ("farmer", "hands"):
            for step in (obs["step"] + 1, obs["step"] + 2, end - 1):
                with self.subTest(actor=actor, step=step):
                    tape = pass_tape()
                    cmd = ["PICKUP", "WHEAT", 1]
                    tape[step][actor] = cmd if actor == "farmer" else [cmd]
                    parent = action()
                    self.assertIs(lane._consider_hire(
                        obs, parent, lane._Day(4), tape, CONFIG), parent)


    def test_next_day_wheat_pickup_does_not_block_current_day(self):
        obs = observation()
        tape = pass_tape()
        tape[(obs["step"] // 24 + 1) * 24]["farmer"] = ["PICKUP", "WHEAT", 1]
        self.assertEqual(lane._consider_hire(
            obs, action(), lane._Day(4), tape, CONFIG)["market"], [["HIRE"]])


    def test_other_product_pickup_remains_eligible(self):
        obs = observation()
        tape = pass_tape()
        tape[obs["step"] + 2]["farmer"] = ["PICKUP", "CARROT", 1]
        self.assertEqual(lane._consider_hire(
            obs, action(), lane._Day(4), tape, CONFIG)["market"], [["HIRE"]])


    def test_f2_cash_floor_selector(self):
        for flag in (False, True, None, 0, 1, "False", [], {}):
            with self.subTest(flag=flag):
                router = SimpleNamespace(FEED_PREBUY=flag)
                with patch.dict(sys.modules, {"r04_full_router": router}):
                    expected = 100.0 if flag is False else 1000.0
                    self.assertEqual(lane._effective_cash_reserve(), expected)
        with patch.dict(sys.modules, {"r04_full_router": SimpleNamespace()}):
            self.assertEqual(lane._effective_cash_reserve(), 100.0)
        with patch.dict(sys.modules, {"r04_full_router": None}):
            self.assertEqual(lane._effective_cash_reserve(), 1000.0)


    def test_f2_cash_floor_exact_boundary_and_standalone_preservation(self):
        for flag, reserve in ((False, 100.0), (True, 1000.0), (None, 1000.0)):
            for hires in (0, 2, 5):
                cost = lane._fib(hires)
                with self.subTest(flag=flag, hires=hires):
                    with patch.dict(sys.modules, {
                        "r04_full_router": SimpleNamespace(FEED_PREBUY=flag)
                    }):
                        parent = action()
                        low = observation(hires_today=hires, money=reserve + cost - 0.25)
                        self.assertIs(lane._consider_hire(
                            low, parent, lane._Day(4), pass_tape(), CONFIG), parent)
                        exact = observation(hires_today=hires, money=reserve + cost)
                        self.assertEqual(lane._consider_hire(
                            exact, action(), lane._Day(4), pass_tape(), CONFIG
                        )["market"], [["HIRE"]])


    def test_malformed_hidden_parent_output_preserves_identity_and_telemetry(self):
        obs = observation(
            step=4 * 24 + 15, hands=[[4, 4], [4, 3], [3, 4]],
            inventories=[{}, {}, {}, {}])
        variants = [
            {}, None, [],
            {"farmer": ["PASS"], "market": []},
            {"hands": None}, {"hands": ()},
            {"hands": []}, {"hands": [["PASS"]]},
            {"hands": [["PASS"]] * 3},
            {"hands": [["PASS"], "EAST"]},
            {"hands": [["PASS"], None]},
        ]
        for sentinel in variants:
            with self.subTest(sentinel=sentinel):
                st = lane._STATE[0] = lane._Day(4)
                st.index = 1
                st.last_step = obs["step"] - 1
                before = copy.deepcopy(sentinel)
                telemetry = dict(lane.REPORT)
                wrapped = lane.wrap(lambda o, c: sentinel, lambda o: pass_tape())
                self.assertIs(wrapped(obs, CONFIG), sentinel)
                self.assertEqual(sentinel, before)
                self.assertEqual(lane.REPORT, telemetry)


    def test_hidden_hand_insertion_preserves_every_parent_index(self):
        for total in range(1, 7):
            for index in range(total):
                with self.subTest(total=total, index=index):
                    hands = [[4, 4] for _ in range(total)]
                    hands[index] = [4, 3]
                    inventories = [{"CARROT": i} for i in range(total + 1)]
                    obs = observation(step=4 * 24 + 15, hands=hands,
                                      inventories=inventories)
                    original_obs = copy.deepcopy(obs)
                    st = lane._STATE[0] = lane._Day(4)
                    st.index = index
                    st.last_step = obs["step"] - 1
                    commands = [["PASS", i] for i in range(total - 1)]
                    sentinel = action(hands=commands)
                    original_action = copy.deepcopy(sentinel)
                    seen = []
                    def parent(view, config):
                        seen.append(view)
                        return sentinel
                    out = lane.wrap(parent, lambda o: pass_tape())(obs, CONFIG)
                    self.assertEqual(out["hands"], commands[:index] +
                                     [["COLLECT_FERTILIZER"]] + commands[index:])
                    self.assertEqual(obs, original_obs)
                    self.assertEqual(sentinel, original_action)
                    self.assertIsNot(out, sentinel)
                    self.assertEqual(seen[0]["private"]["inventories"],
                                     inventories[:index + 1] + inventories[index + 2:])
                    self.assertEqual(seen[0]["farms"][0]["hires_today"],
                                     obs["farms"][0]["hires_today"])


    def test_unrepresentable_fertilizer_quote_fails_closed(self):
        for price in (10 ** 10000, 10 ** 308):
            obs, parent = observation(fertilizer_price=price), action()
            self.assertIs(lane._consider_hire(
                obs, parent, lane._Day(4), pass_tape(), CONFIG), parent)



if __name__ == "__main__":
    unittest.main()
