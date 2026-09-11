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
import h3b_maxheld_harvest as h3b  # noqa: E402


STEP = 18 * 24 + 10
TARGETS = [(5, 5), (6, 5), (7, 5)]


def sheep(*, units=1, placed=13, fed=True, cared=True, bonus=1):
    return {
        "kind": "PASTURE",
        "animal": "SHEEP",
        "placed_day": placed,
        "yield_units": units,
        "consecutive_unfed": 0,
        "fed_today": fed,
        "cared_today": cared,
        "fertilizer_available": True,
        "pending_care_bonus": bonus,
    }


def fixture(*, step=STEP, position=(5, 5), inventory=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[5][5] = sheep(units=1)
    tiles[5][6] = sheep(units=6)
    tiles[5][7] = sheep(units=1)
    action = {"farmer": ["PASS"], "hands": [["HARVEST"]], "market": []}
    observation = {
        "step": step,
        "player": 0,
        "farms": [{"farmer": [4, 4], "hands": [list(position)], "tiles": tiles}],
        "private": {"inventories": [{}, dict(inventory or {})], "shed": {}},
    }
    state = {
        "last_step": step,
        "day": step // 24,
        "workers": {1: list(TARGETS)},
        "work": {1: {"step": step, "command": ["HARVEST"], "inventory": dict(inventory or {})}},
        "credit": {"WOOL": 0, "FERTILIZER": 0},
        "committed": True,
    }
    return action, observation, state


class H3bContracts(unittest.TestCase):
    def setUp(self):
        self.saved_states = base._V233_STATES
        base._V233_STATES = {}

    def tearDown(self):
        base._V233_STATES = self.saved_states

    def run_case(self, action, observation, state, *, enabled=True, configuration=None):
        base._V233_STATES[0] = state
        return h3b.reprioritize(action, observation, configuration, enabled=enabled)

    def test_disabled_is_exact_parent_identity(self):
        action, observation, state = fixture()
        result = self.run_case(action, observation, state, enabled=False)
        self.assertIs(result, action)
        self.assertEqual(state["work"][1]["command"], ["HARVEST"])

    def test_overflowing_sheep_preempts_nearer_nonurgent_harvest(self):
        action, observation, state = fixture()
        result = self.run_case(action, observation, state)
        self.assertIsNot(result, action)
        self.assertEqual(action["hands"][0], ["HARVEST"])
        self.assertEqual(result["hands"][0], ["EAST"])
        self.assertEqual(state["work"][1]["command"], ["EAST"])

    def test_already_on_urgent_sheep_is_identity(self):
        action, observation, state = fixture(position=(6, 5))
        result = self.run_case(action, observation, state)
        self.assertIs(result, action)
        self.assertEqual(state["work"][1]["command"], ["HARVEST"])

    def test_no_imminent_overflow_is_identity(self):
        action, observation, state = fixture()
        observation["farms"][0]["tiles"][5][6]["yield_units"] = 4
        result = self.run_case(action, observation, state)
        self.assertIs(result, action)

    def test_not_a_production_refresh_is_identity(self):
        action, observation, state = fixture()
        for x, _y in TARGETS:
            observation["farms"][0]["tiles"][5][x]["placed_day"] = 12
        result = self.run_case(action, observation, state)
        self.assertIs(result, action)

    def test_feed_or_care_debt_blocks_override(self):
        for field in ("fed_today", "cared_today"):
            with self.subTest(field=field):
                action, observation, state = fixture()
                observation["farms"][0]["tiles"][5][7][field] = False
                result = self.run_case(action, observation, state)
                self.assertIs(result, action)
                self.assertEqual(state["work"][1]["command"], ["HARVEST"])

    def test_cargo_return_priority_blocks_override(self):
        for item in ("WOOL", "FERTILIZER"):
            with self.subTest(item=item):
                action, observation, state = fixture(inventory={item: 1})
                result = self.run_case(action, observation, state)
                self.assertIs(result, action)

    def test_setup_or_missing_sheep_blocks_override(self):
        action, observation, state = fixture()
        observation["farms"][0]["tiles"][5][7] = None
        result = self.run_case(action, observation, state)
        self.assertIs(result, action)

    def test_malformed_json_scalar_types_fail_closed(self):
        mutations = (
            ("yield_units", True),
            ("yield_units", 6.0),
            ("placed_day", "13"),
            ("pending_care_bonus", 1.0),
            ("fed_today", 1),
            ("cared_today", 1),
        )
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                action, observation, state = fixture()
                observation["farms"][0]["tiles"][5][6][key] = value
                result = self.run_case(action, observation, state)
                self.assertIs(result, action)

    def test_nonstandard_configuration_fails_closed_without_coercion(self):
        for configuration in (
            {"turnsPerDay": 12},
            {"turnsPerDay": "24"},
            {"turnsPerDay": 24.0},
            {"turnsPerDay": True},
            {"shedCapacity": 99},
        ):
            with self.subTest(configuration=configuration):
                action, observation, state = fixture()
                result = self.run_case(action, observation, state, configuration=configuration)
                self.assertIs(result, action)

    def test_v233_same_call_snapshot_mismatch_fails_closed(self):
        action, observation, state = fixture()
        state["work"][1]["command"] = ["CARE"]
        result = self.run_case(action, observation, state)
        self.assertIs(result, action)
        self.assertEqual(state["work"][1]["command"], ["CARE"])

    def test_final_day_is_identity(self):
        action, observation, state = fixture(step=29 * 24 + 10)
        state["last_step"] = observation["step"]
        state["work"][1]["step"] = observation["step"]
        result = self.run_case(action, observation, state)
        self.assertIs(result, action)

    def test_parent_action_is_not_mutated_on_override(self):
        action, observation, state = fixture()
        before = copy.deepcopy(action)
        result = self.run_case(action, observation, state)
        self.assertEqual(action, before)
        self.assertNotEqual(result, before)


if __name__ == "__main__":
    unittest.main()
