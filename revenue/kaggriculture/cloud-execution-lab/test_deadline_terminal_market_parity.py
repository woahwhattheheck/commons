# SPDX-License-Identifier: Apache-2.0
"""Engine-parity regressions for the deadline terminal fallback."""
import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "reference/titan-current/deadline_adapter.py"
SPEC = importlib.util.spec_from_file_location("deadline_adapter_under_test", SOURCE)
DEADLINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEADLINE)


CONFIG = {
    "episodeSteps": 720,
    "turnsPerDay": 24,
    "boardSize": 10,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
}


def observation(*, shed, inventory=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    return {
        "player": 0,
        "farms": [{"farmer": [4, 4], "hands": [], "tiles": tiles}],
        "private": {
            "shed": dict(shed),
            "inventories": [dict(inventory or {})],
        },
    }


def runtime_observation(*, step=718, day=29, hour=22, shed=None,
                        farmer=(4, 4), hands=(), inventories=None,
                        include_clock=True):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    positions = [list(farmer), *[list(position) for position in hands]]
    if inventories is None:
        inventories = [{} for _ in positions]
    obs = {
        "player": 0,
        "farms": [{
            "farmer": positions[0],
            "hands": positions[1:],
            "tiles": tiles,
        }],
        "private": {
            "shed": dict(shed or {}),
            "inventories": [dict(inv) for inv in inventories],
        },
    }
    if step is not None:
        obs["step"] = step
    if include_clock:
        obs["day"] = day
        obs["hour"] = hour
    return obs


class _Production:
    def __init__(self, action):
        self.action = action
        self.calls = 0
        self.last_observation = None

    def act(self, observation):
        self.calls += 1
        self.last_observation = copy.deepcopy(observation)
        return copy.deepcopy(self.action)


class _Integrated:
    def __init__(self, action, *, output=None, timeout_transform=False):
        self.production = _Production(action)
        self.output = output
        self.timeout_transform = timeout_transform
        self.transform_calls = 0
        self.diagnostics = {}

    def transform(self, observation, configuration, selected, fallback_action=None):
        self.transform_calls += 1
        if self.timeout_transform:
            timer = DEADLINE._ACTIVE_TIMER.get()
            if timer is None:
                raise AssertionError("deadline timer was not active")
            raise timer.expired
        return copy.deepcopy(selected if self.output is None else self.output)


def guarded(action, **kwargs):
    integrated = _Integrated(action, **kwargs)
    return DEADLINE.DeadlineFallbackAgent(
        integrated, budget_seconds=0.25, reserve_seconds=0.0
    ), integrated


class DeadlineTerminalMarketParityTests(unittest.TestCase):
    def test_engine_effective_market_cap_clamps_zero_and_negative_to_one(self):
        obs = observation(shed={"GOOSE": 4, "WHEAT": 2, "CARROT": 3})
        expected = [["SELL", "WHEAT", 2]]
        for limit in (0, -3):
            with self.subTest(limit=limit):
                action = DEADLINE.terminal_liquidation_fallback(
                    obs, {"maxMarketOrdersPerTurn": limit}
                )
                self.assertEqual(action["market"], expected)

    def test_unsaleable_animals_are_not_emitted_as_sell_rows(self):
        obs = observation(
            shed={"GOOSE": 2, "WHEAT": 3, "COW": 1, "MILK": 4, "SHEEP": 5}
        )
        action = DEADLINE.terminal_liquidation_fallback(obs, {})
        self.assertEqual(
            action["market"],
            [["SELL", "WHEAT", 3], ["SELL", "MILK", 4]],
        )

    def test_animal_stock_still_consumes_shed_capacity_for_terminal_drop(self):
        obs = observation(shed={"GOOSE": 99}, inventory={"WHEAT": 2})
        action = DEADLINE.terminal_liquidation_fallback(
            obs, {"shedCapacity": 100, "maxMarketOrdersPerTurn": 10}
        )
        self.assertEqual(action["farmer"], ["DROP"])
        self.assertEqual(action["market"], [["SELL", "WHEAT", 1]])

    def test_player_aliases_never_select_a_different_farm(self):
        for player in (True, "0", 0.0, -1, 1):
            with self.subTest(player=player):
                obs = observation(shed={"WHEAT": 1})
                obs["player"] = player
                with self.assertRaises(ValueError):
                    DEADLINE.legal_pass(obs)
                with self.assertRaises(ValueError):
                    DEADLINE.terminal_liquidation_fallback(obs, {})

    def test_step_aliases_fail_before_producer_dispatch(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        for step in (True, "718", 718.0, -1):
            with self.subTest(step=step):
                agent, integrated = guarded(action)
                obs = runtime_observation(step=step, include_clock=False)
                with self.assertRaises(ValueError):
                    agent.act(obs, CONFIG)
                self.assertEqual(integrated.production.calls, 0)
                self.assertEqual(integrated.transform_calls, 0)

    def test_redundant_or_partial_public_clock_must_agree(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        cases = [
            runtime_observation(step=718, day=29, hour=21),
            runtime_observation(step=718, include_clock=False),
        ]
        cases[1]["day"] = 29
        for obs in cases:
            agent, integrated = guarded(action)
            with self.assertRaises(ValueError):
                agent.act(obs, CONFIG)
            self.assertEqual(integrated.production.calls, 0)

    def test_exact_day_hour_fallback_injects_canonical_step(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        obs = runtime_observation(step=None, day=29, hour=22, inventories=[{}])
        agent, integrated = guarded(action)
        self.assertEqual(agent.act(obs, CONFIG), action)
        self.assertEqual(integrated.production.last_observation["step"], 718)

    def test_terminal_normal_return_converts_adjacent_cargo_without_market_edit(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "WHEAT", 2], ["BUY_LAND"]],
        }
        obs = runtime_observation(shed={"WHEAT": 5}, inventories=[{"WHEAT": 2}])
        config = dict(CONFIG, shedCapacity=10)
        agent, _integrated = guarded(action)
        result = agent.act(obs, config)
        self.assertEqual(result["farmer"], ["DROP"])
        self.assertEqual(result["hands"], [])
        self.assertEqual(result["market"], action["market"])

    def test_terminal_cashout_is_atomic_across_all_adjacent_carriers(self):
        action = {
            "farmer": ["PASS"],
            "hands": [["PASS"]],
            "market": [["SELL", "WHEAT", 2], ["SELL", "MILK", 2]],
        }
        positions = ((5, 4),)
        inventories = [{"WHEAT": 2}, {"MILK": 2}]
        exact_fit = runtime_observation(
            shed={"GOOSE": 6}, hands=positions, inventories=inventories
        )
        agent, _integrated = guarded(action)
        result = agent.act(exact_fit, dict(CONFIG, shedCapacity=10))
        self.assertEqual(result["farmer"], ["DROP"])
        self.assertEqual(result["hands"], [["DROP"]])
        self.assertEqual(result["market"], action["market"])

        over_capacity = runtime_observation(
            shed={"GOOSE": 7}, hands=positions, inventories=inventories
        )
        agent, _integrated = guarded(action)
        self.assertEqual(
            agent.act(over_capacity, dict(CONFIG, shedCapacity=10)),
            action,
        )

    def test_nonterminal_adjacent_cargo_preserves_selected_action(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "WHEAT", 2]],
        }
        obs = runtime_observation(
            step=717, day=29, hour=21, shed={"WHEAT": 5},
            inventories=[{"WHEAT": 2}],
        )
        agent, _integrated = guarded(action)
        self.assertEqual(agent.act(obs, dict(CONFIG, shedCapacity=10)), action)

    def test_transform_timeout_uses_terminal_carry_safe_selected_fallback(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "WHEAT", 2]],
        }
        obs = runtime_observation(shed={"WHEAT": 5}, inventories=[{"WHEAT": 2}])
        agent, integrated = guarded(action, timeout_transform=True)
        result = agent.act(obs, dict(CONFIG, shedCapacity=10))
        self.assertEqual(integrated.transform_calls, 1)
        self.assertEqual(result["farmer"], ["DROP"])
        self.assertEqual(result["market"], action["market"])
        self.assertEqual(agent.diagnostics["fallback_stage"], "transform")

    def test_terminal_carry_rewrite_fails_closed_on_coercible_config(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "WHEAT", 2]],
        }
        obs = runtime_observation(shed={"WHEAT": 5}, inventories=[{"WHEAT": 2}])
        for patch in ({"shedCapacity": "10"}, {"episodeSteps": 720.0}):
            with self.subTest(patch=patch):
                config = dict(CONFIG)
                config.update(patch)
                agent, _integrated = guarded(action)
                self.assertEqual(agent.act(obs, config), action)


if __name__ == "__main__":
    unittest.main(verbosity=2)
