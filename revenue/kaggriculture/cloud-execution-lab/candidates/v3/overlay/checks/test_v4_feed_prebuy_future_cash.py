# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import sys
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_feed_prebuy as lane
import r04_full_router as r04


def _tile_grid():
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[4][6] = {
        "animal": "GOOSE",
        "fed_today": False,
        "consecutive_unfed": 1,
    }
    return tiles


def _observation():
    return {
        "step": 39,
        "player": 0,
        "farms": [{
            "money": 5000.0,
            "farmer": [4, 4],
            "hands": [],
            "tiles": _tile_grid(),
        }],
        "private": {
            "shed": {"WHEAT": 0},
            "inventories": [{}],
        },
        "market": {
            "inventory": {"WHEAT": 10000},
            "prices": {
                "WHEAT": 30,
                "EGG": 100,
                "MILK": 100,
                "WOOL": 100,
                "FERTILIZER": 10,
                "CARROT": 50,
                "TOMATO": 50,
                "STRAWBERRY": 50,
                "MELON": 50,
            }
        },
    }


def _action():
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _standard_config():
    return {
        "episodeSteps": 720,
        "boardSize": 10,
        "turnsPerDay": 24,
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
        "marketParams": {},
    }


class FeedPrebuyFutureCashTests(unittest.TestCase):
    def setUp(self):
        self.old_policy = r04._POLICY
        self.tape = [
            {"farmer": ["PASS"], "hands": [], "market": []}
            for _ in range(719)
        ]
        state = SimpleNamespace(
            plan=0,
            last_step=39,
            day=1,
            queues={},
            v217_used=0,
            v217_task=None,
        )
        r04._POLICY = SimpleNamespace(players={0: state}, tapes=[self.tape])

    def tearDown(self):
        r04._POLICY = self.old_policy

    def _apply(self, parent):
        return lane.apply_feed_prebuy(
            _observation(), parent, configuration=_standard_config(), enabled=True)

    def test_remaining_day_cash_spenders_are_hard_barriers(self):
        spend_rows = (
            ["HIRE"],
            ["BUY_LAND"],
            ["BUY_PRODUCT", "FERTILIZER", 1],
            ["BUY_SEED", "WHEAT", 1],
            ["BUY_ANIMAL", "GOOSE", 1],
        )
        for row in spend_rows:
            with self.subTest(row=row):
                self.tape[40]["market"] = [row]
                parent = _action()
                self.assertIs(self._apply(parent), parent)
                self.tape[40]["market"] = []

    def test_later_buy_land_starvation_witness_fails_closed(self):
        # F2's flat $1k reserve must not be allowed to fund the rescue by
        # stealing cash from a literal purchase already authored for h16+.
        self.tape[47]["market"] = [["BUY_LAND"]]
        parent = _action()
        self.assertIs(self._apply(parent), parent)

    def test_next_day_purchase_does_not_block_hour15_prebuy(self):
        self.tape[48]["market"] = [["BUY_LAND"]]
        out = self._apply(_action())
        self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", 2]])

    def test_future_sell_is_not_a_cash_spend_barrier(self):
        self.tape[40]["market"] = [["SELL", "CARROT", 1]]
        out = self._apply(_action())
        self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", 2]])

    def test_malformed_future_market_rows_fail_closed(self):
        for row in ({"verb": "BUY_LAND"}, [], None, "", 0, False):
            with self.subTest(row=row):
                self.tape[40]["market"] = [row]
                parent = _action()
                self.assertIs(self._apply(parent), parent)
                self.tape[40]["market"] = []


class FeedPrebuyTailCompositionTests(unittest.TestCase):
    """Counterfactuals must use the same native-first planner as production.

    The optional F3-module cases run once #12638 is in the materialized tree.
    Before then, the native-only/OFF and missing-module cases remain executable.
    """
    setUp = FeedPrebuyFutureCashTests.setUp
    tearDown = FeedPrebuyFutureCashTests.tearDown

    def _far_observation(self, wheat=0, target=(9, 5)):
        observation = _observation()
        tile = observation["farms"][0]["tiles"][4][6]
        tile["kind"] = "COOP"
        observation["farms"][0]["tiles"][4][6] = None
        observation["farms"][0]["tiles"][target[1]][target[0]] = tile
        observation["farms"].append(copy.deepcopy(observation["farms"][0]))
        observation["private"]["shed"]["WHEAT"] = wheat
        return observation

    def _tail(self):
        try:
            import r04_v217_eod_tail as tail
        except ImportError:
            self.skipTest("F3 module is not yet in this serial package")
        if not hasattr(tail, "plan_v217_eod_tail"):
            self.skipTest("pre-wrapper F3 donor is not the current F3 contract")
        return tail

    def _apply_far(self, observation, configuration=None):
        config = _standard_config() if configuration is None else configuration
        parent = _action()
        with mock.patch.object(r04, "V217_EOD_TAIL", True, create=True):
            return parent, lane.apply_feed_prebuy(
                observation, parent, configuration=config, enabled=True)

    def test_native_planner_keeps_five_argument_abi_and_positive_identity(self):
        native = {"target": (6, 4), "commands": [["FEED"]]}
        with mock.patch.object(r04, "_v217_plan", return_value=native) as planner:
            with mock.patch.object(r04, "V217_EOD_TAIL", True, create=True):
                with mock.patch.dict(sys.modules, {"r04_v217_eod_tail": None}):
                    result = lane._next_v217_task(_observation(), _action(), 2, r04)
        self.assertIs(result, native)
        self.assertEqual(len(planner.call_args.args), 5)
        self.assertEqual(planner.call_args.kwargs, {})

    def test_tail_off_preserves_native_prebuy_without_importing_f3(self):
        parent = _action()
        with mock.patch.object(r04, "V217_EOD_TAIL", False, create=True):
            with mock.patch.dict(sys.modules, {"r04_v217_eod_tail": None}):
                out = lane.apply_feed_prebuy(
                    _observation(), parent, configuration=_standard_config(), enabled=True)
        self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", 2]])
        self.assertEqual(parent, _action())

    def test_f2_off_is_exact_identity_even_when_tail_is_on(self):
        parent = _action()
        with mock.patch.object(r04, "V217_EOD_TAIL", True, create=True):
            self.assertIs(lane.apply_feed_prebuy(None, parent, enabled=False), parent)

    def test_missing_tail_module_cannot_crash_or_authorize_a_buy(self):
        observation = self._far_observation()
        with mock.patch.dict(sys.modules, {"r04_v217_eod_tail": None}):
            parent, out = self._apply_far(observation)
        self.assertIs(out, parent)

    def test_two_wheat_unlocks_exact_final_callback_tail(self):
        tail = self._tail()
        observation = self._far_observation()
        snapshot = copy.deepcopy(observation)
        state_before = copy.deepcopy(vars(r04._POLICY.players[0]))
        tape_before = copy.deepcopy(self.tape)
        config = _standard_config()
        with mock.patch.object(tail, "plan_v217_eod_tail", wraps=tail.plan_v217_eod_tail) as probe:
            parent, out = self._apply_far(observation, config)
        self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", 2]])
        self.assertEqual(parent, _action())
        self.assertEqual(observation, snapshot)
        self.assertEqual(vars(r04._POLICY.players[0]), state_before)
        self.assertEqual(self.tape, tape_before)
        self.assertEqual(probe.call_count, 3)
        for call in probe.call_args_list:
            self.assertIs(call.kwargs["configuration"], config)
            self.assertIs(call.kwargs["tape"], self.tape)
            self.assertIs(call.kwargs["enabled"], True)
        # This is the actual production native-first/fallback decision at h16.
        funded = copy.deepcopy(observation)
        funded["private"]["shed"]["WHEAT"] = 2
        view = r04.FarmView(funded)
        st = vars(r04._POLICY.players[0])
        next_action = self.tape[40]
        self.assertIsNone(r04._v217_plan(view, st, 40, next_action, []))
        task = tail.plan_v217_eod_tail(
            view, st, 40, next_action, [], tape=self.tape,
            projected_wheat=r04.projected_shed(next_action, view)["WHEAT"],
            configuration=config, enabled=True)
        self.assertIsNotNone(task)
        self.assertEqual(task["target"], (9, 5))
        self.assertEqual(len(task["commands"]), 8)
        self.assertEqual(task["commands"][0], ["PICKUP", "WHEAT"])
        self.assertEqual(task["commands"][-1], ["FEED"])
        self.assertEqual(task["step"] + len(task["commands"]) - 1, 47)

    def test_one_wheat_increment_is_minimal_for_tail_rescue(self):
        self._tail()
        _, out = self._apply_far(self._far_observation(wheat=1))
        self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", 1]])

    def test_already_funded_tail_preserves_parent_identity(self):
        self._tail()
        parent, out = self._apply_far(self._far_observation(wheat=2))
        self.assertIs(out, parent)

    def test_struct_config_reaches_the_same_tail(self):
        self._tail()
        config = SimpleNamespace(**_standard_config())
        _, out = self._apply_far(self._far_observation(), config)
        self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", 2]])

    def test_unfunded_far_rescue_stays_dead_with_tail_off(self):
        parent = _action()
        with mock.patch.object(r04, "V217_EOD_TAIL", False, create=True):
            out = lane.apply_feed_prebuy(
                self._far_observation(), parent, configuration=_standard_config(), enabled=True)
        self.assertIs(out, parent)

    def test_future_farmer_work_and_purchase_still_veto_tail_prebuy(self):
        self._tail()
        for field, commands in (("farmer", ["WATER"]),
                                ("market", [["BUY_LAND"]])):
            with self.subTest(field=field):
                prior = self.tape[47][field]
                self.tape[47][field] = commands
                parent, out = self._apply_far(self._far_observation())
                self.assertIs(out, parent)
                self.tape[47][field] = prior

    def test_multiple_far_targets_preserve_parent_identity(self):
        self._tail()
        observation = self._far_observation()
        observation["farms"][0]["tiles"][9][5] = copy.deepcopy(
            observation["farms"][0]["tiles"][5][9])
        parent, out = self._apply_far(observation)
        self.assertIs(out, parent)

    def test_final_partial_day_cannot_enable_tail_prebuy(self):
        self._tail()
        observation = self._far_observation(target=(9, 4))
        observation["step"] = 711
        r04._POLICY.players[0].last_step = 711
        parent, out = self._apply_far(observation)
        self.assertIs(out, parent)

    def test_next_hand_pickup_uses_projected_shed_not_raw_shed(self):
        self._tail()
        observation = self._far_observation()
        observation["farms"][0]["hands"] = [[4, 4]]
        observation["private"]["inventories"].append({})
        parent = {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}
        with mock.patch.object(r04, "V217_EOD_TAIL", True, create=True):
            control = lane.apply_feed_prebuy(
                observation, parent, _standard_config(), True)
            self.assertEqual(control["market"], [["BUY_PRODUCT", "WHEAT", 2]])
            self.tape[40]["hands"] = [["PICKUP", "WHEAT", 1]]
            out = lane.apply_feed_prebuy(
                observation, parent, _standard_config(), True)
        self.assertIs(out, parent)

    def test_tail_prebuy_keeps_plus25_funding_boundary(self):
        self._tail()
        for money, allowed in ((1109.0, False), (1110.0, True)):
            with self.subTest(money=money):
                observation = self._far_observation()
                observation["farms"][0]["money"] = money
                parent, out = self._apply_far(observation)
                if allowed:
                    self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", 2]])
                else:
                    self.assertIs(out, parent)

    def test_incomplete_tape_is_already_rejected_by_native_planner(self):
        del self.tape[41:]
        parent = _action()
        with mock.patch.object(r04, "V217_EOD_TAIL", False, create=True):
            out = lane.apply_feed_prebuy(
                _observation(), parent, configuration=_standard_config(), enabled=True)
        self.assertIs(out, parent)


if __name__ == "__main__":
    unittest.main()