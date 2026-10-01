# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parent / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import h9_r04_e20_hire_guard as h9  # noqa: E402


def plant(*, watered=False):
    return {"kind": "PLANT", "watered_today": watered}


def obs(*, step=40, hires_today=0, tiles=None, hands=0):
    farm = {
        "money": 5000,
        "hires_today": hires_today,
        "tiles": tiles if tiles is not None else [[None]],
        "hands": [[0, 0] for _ in range(hands)],
        "unlocked_quadrants": ["NW"],
    }
    rival = {
        "money": 5000,
        "hires_today": 0,
        "tiles": [[None]],
        "hands": [],
        "unlocked_quadrants": ["NW"],
    }
    return {"step": step, "player": 0, "farms": [farm, rival], "market": {"prices": {}}}


def parent_with(action):
    def parent(_observation, _configuration=None):
        return action
    return parent


class H9R04E20Tests(unittest.TestCase):
    def tearDown(self):
        globals().pop("_V219_REPORT", None)
        globals().pop("_V233_REPORT", None)

    def test_disabled_is_exact_parent_output_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"]]}
        arm = h9.install(parent_with(action), enabled=False)
        self.assertIs(arm(obs(), {}), action)
        self.assertEqual(arm.telemetry["changed"], 0)
        self.assertEqual(arm.telemetry["activation_trace"], [])
        self.assertEqual(arm.telemetry["reasons"]["OFF"], 1)

    def test_low_demand_blanks_only_excess_hires_and_preserves_indices(self):
        rows = [["SELL", "WHEAT", 2], ["HIRE"], ["BUY_ANIMAL", "COW"], ["HIRE"]]
        action = {"farmer": ["PASS"], "hands": [], "market": deepcopy(rows)}
        arm = h9.install(parent_with(action), enabled=True, max_hires_per_day=3)
        out = arm(obs(hires_today=3), {})
        self.assertEqual(action["market"], rows)
        self.assertEqual(out["market"], [rows[0], [], rows[2], []])
        self.assertEqual(len(out["market"]), len(rows))
        self.assertEqual(arm.telemetry["changed"], 1)
        self.assertEqual(arm.telemetry["dropped_hire_rows"], 2)
        self.assertEqual(arm.telemetry["coupled_investment_activations"], 1)
        event = arm.telemetry["activation_trace"][0]
        self.assertEqual(event["original_hire_indices"], [1, 3])
        self.assertEqual(event["dropped_hire_indices"], [1, 3])
        self.assertEqual(event["coupled_investment_rows"], [{"index": 2, "order": ["BUY_ANIMAL", "COW"]}])

    def test_low_demand_allowance_keeps_earliest_hire_then_blanks_later_hires(self):
        rows = [["HIRE"], ["SELL", "MILK", 1], ["HIRE"], ["HIRE"]]
        action = {"farmer": ["PASS"], "hands": [], "market": deepcopy(rows)}
        arm = h9.install(parent_with(action), enabled=True, max_hires_per_day=3)
        out = arm(obs(hires_today=2), {})
        self.assertEqual(out["market"], [["HIRE"], rows[1], [], []])
        self.assertEqual(arm.telemetry["dropped_hire_rows"], 2)
        self.assertEqual(arm.telemetry["activation_trace"][0]["original_hire_indices"], [0, 2, 3])
        self.assertEqual(arm.telemetry["activation_trace"][0]["dropped_hire_indices"], [2, 3])

    def test_v219_day18_coupled_capital_is_explicitly_traced(self):
        rows = [["BUY_LAND"], ["BUY_SEED", "TOMATO", 10], ["HIRE"], ["HIRE"]]
        action = {"farmer": ["PASS"], "hands": [], "market": deepcopy(rows)}
        arm = h9.install(parent_with(action), enabled=True, max_hires_per_day=0)
        out = arm(obs(step=18 * 24, hands=4), {})
        self.assertEqual(out["market"], [rows[0], rows[1], [], []])
        event = arm.telemetry["activation_trace"][0]
        self.assertEqual(event["day"], 18)
        self.assertEqual(event["step"], 432)
        self.assertEqual(event["original_hire_indices"], [2, 3])
        self.assertEqual(event["dropped_hire_indices"], [2, 3])
        self.assertEqual(
            event["coupled_investment_rows"],
            [{"index": 0, "order": ["BUY_LAND"]}, {"index": 1, "order": ["BUY_SEED", "TOMATO", 10]}],
        )
        self.assertEqual(event["settlement"], "PENDING")

    def test_next_observation_settles_hand_and_v219_shortfall_evidence(self):
        global _V219_REPORT
        _V219_REPORT = {"hire_shortfalls": 7}
        rows = [["BUY_LAND"], ["BUY_SEED", "TOMATO", 10], ["HIRE"], ["HIRE"]]
        action = {"farmer": ["PASS"], "hands": [], "market": deepcopy(rows)}
        arm = h9.install(parent_with(action), enabled=True, max_hires_per_day=0)
        arm(obs(step=432, hands=4), {})
        _V219_REPORT["hire_shortfalls"] = 9
        arm(obs(step=433, hands=4), {})
        first = arm.telemetry["activation_trace"][0]
        self.assertEqual(first["settlement"], "NEXT_OBSERVATION")
        self.assertEqual(first["hands_next_observation"], 4)
        self.assertEqual(first["observed_hand_delta"], 0)
        self.assertEqual(first["v219_hire_shortfall_delta"], 2)
        self.assertEqual(arm.telemetry["settled_activations"], 1)
        self.assertEqual(arm.telemetry["v219_hire_shortfall_delta"], 2)

    def test_changed_is_not_claimed_as_realized_hand_reduction(self):
        rows = [["HIRE"], ["HIRE"]]
        action = {"farmer": ["PASS"], "hands": [], "market": deepcopy(rows)}
        arm = h9.install(parent_with(action), enabled=True, max_hires_per_day=0)
        arm(obs(step=40, hands=2), {})
        self.assertEqual(arm.telemetry["changed"], 1)
        self.assertEqual(arm.telemetry["activation_trace"][0]["settlement"], "PENDING")
        arm(obs(step=41, hands=2), {})
        first = arm.telemetry["activation_trace"][0]
        self.assertEqual(first["observed_hand_delta"], 0)
        self.assertEqual(first["settlement"], "NEXT_OBSERVATION")

    def test_episode_reset_marks_pending_activation_unresolved(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"]]}
        arm = h9.install(parent_with(action), enabled=True, max_hires_per_day=0)
        arm(obs(step=40), {})
        arm(obs(step=0), {})
        first = arm.telemetry["activation_trace"][0]
        self.assertEqual(first["settlement"], "EPISODE_RESET")
        self.assertEqual(arm.telemetry["unresolved_on_reset"], 1)

    def test_unwatered_crop_demand_preserves_every_hire(self):
        rows = [["HIRE"], ["SELL", "WOOL", 1], ["HIRE"], ["HIRE"]]
        action = {"farmer": ["PASS"], "hands": [], "market": deepcopy(rows)}
        tiles = [[plant(), plant(), plant()]]
        arm = h9.install(parent_with(action), enabled=True, min_unwatered_crops=3)
        out = arm(obs(hires_today=3, tiles=tiles), {})
        self.assertIs(out, action)
        self.assertEqual(out["market"], rows)
        self.assertEqual(arm.telemetry["reasons"]["DEMAND_JUSTIFIES_HIRES"], 1)

    def test_watered_plants_do_not_count_as_demand(self):
        rows = [["HIRE"], ["HIRE"]]
        action = {"farmer": ["PASS"], "hands": [], "market": deepcopy(rows)}
        tiles = [[plant(watered=True), plant(watered=True), plant(watered=True)]]
        arm = h9.install(parent_with(action), enabled=True, max_hires_per_day=0)
        out = arm(obs(tiles=tiles), {})
        self.assertEqual(out["market"], [[], []])

    def test_terminal_step_is_exact_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"], ["HIRE"]]}
        arm = h9.install(parent_with(action), enabled=True, max_hires_per_day=0)
        out = arm(obs(step=718), {"episodeSteps": 720})
        self.assertIs(out, action)
        self.assertEqual(arm.telemetry["reasons"]["NO_EDIT_TERMINAL_STEP"], 1)

    def test_no_hire_is_exact_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "STRAWBERRY", 7]]}
        arm = h9.install(parent_with(action), enabled=True)
        out = arm(obs(hires_today=9), {})
        self.assertIs(out, action)
        self.assertEqual(arm.telemetry["reasons"]["NO_HIRE"], 1)

    def test_no_change_when_low_demand_hires_are_within_allowance(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"], ["HIRE"]]}
        arm = h9.install(parent_with(action), enabled=True, max_hires_per_day=3)
        out = arm(obs(hires_today=1), {})
        self.assertIs(out, action)
        self.assertEqual(arm.telemetry["reasons"]["HIRES_WITHIN_LOW_DEMAND_ALLOWANCE"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
