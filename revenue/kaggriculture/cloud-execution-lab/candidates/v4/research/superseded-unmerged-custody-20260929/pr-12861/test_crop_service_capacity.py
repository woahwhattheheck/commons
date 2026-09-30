# SPDX-License-Identifier: Apache-2.0
import copy
import importlib.util
from pathlib import Path
import unittest
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("crop_service_capacity", HERE / "crop_service_capacity.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def obs(*, hour=0, hands=0, empty=25, player=0):
    side = 5
    cells = [None] * empty + [{"kind": "WEED"}] * (side * side - empty)
    rows = [cells[i:i + side] for i in range(0, len(cells), side)]
    farm = {
        "farmer": [2, 2],
        "hands": [[2, 2] for _ in range(hands)],
        "tiles": rows,
    }
    return {"player": player, "hour": hour, "farms": [farm]}


class CapacityTests(unittest.TestCase):
    def test_opening_current_labor_cap_is_twelve(self):
        e = mod.capacity_envelope(obs(hour=0, hands=0))
        self.assertEqual(e.callbacks_remaining, 24)
        self.assertEqual(e.current_labor_action_slots, 24)
        self.assertEqual(e.current_labor_ceiling, 12)

    def test_last_hour_one_actor_cannot_establish_plant(self):
        e = mod.capacity_envelope(obs(hour=23, hands=0))
        self.assertEqual(e.current_labor_action_slots, 1)
        self.assertEqual(e.future_hire_action_slots_upper, 0)
        self.assertEqual(e.absolute_action_ceiling, 0)

    def test_last_hour_two_actors_can_have_one_pair_of_unit_actions(self):
        e = mod.capacity_envelope(obs(hour=23, hands=1))
        self.assertEqual(e.absolute_action_ceiling, 1)

    def test_future_hires_are_only_in_absolute_bound(self):
        e = mod.capacity_envelope(
            obs(hour=22, hands=0),
            {"turnsPerDay": 24, "maxMarketOrdersPerTurn": 10},
        )
        self.assertEqual(e.current_labor_action_slots, 2)
        self.assertEqual(e.current_labor_ceiling, 1)
        self.assertEqual(e.future_hire_action_slots_upper, 10)
        self.assertEqual(e.absolute_action_ceiling, 6)

    def test_physical_empty_tiles_cap_both_bounds(self):
        e = mod.capacity_envelope(obs(hour=0, hands=4, empty=3))
        self.assertEqual(e.current_labor_ceiling, 3)
        self.assertEqual(e.absolute_action_ceiling, 3)

    def test_locked_or_occupied_tiles_are_not_empty(self):
        o = obs(hour=0, empty=25)
        o["farms"][0]["tiles"][0][0] = "LOCKED"
        o["farms"][0]["tiles"][0][1] = {"kind": "PLANT", "crop": "WHEAT"}
        o["farms"][0]["tiles"][0][2] = {"kind": "COOP"}
        e = mod.capacity_envelope(o)
        self.assertEqual(e.empty_owned_tiles, 22)

    def test_custom_turns_and_market_cap(self):
        e = mod.capacity_envelope(
            obs(hour=4, hands=1),
            {"turnsPerDay": 8, "maxMarketOrdersPerTurn": 2},
        )
        self.assertEqual(e.callbacks_remaining, 4)
        self.assertEqual(e.current_labor_action_slots, 8)
        self.assertEqual(e.future_hire_action_slots_upper, 12)
        self.assertEqual(e.current_labor_ceiling, 4)
        self.assertEqual(e.absolute_action_ceiling, 10)

    def test_conditional_no_hire_rejection(self):
        result = mod.assess_proposed_expansion(
            obs(hour=22), 2, no_future_hires=True
        )
        self.assertEqual(result["verdict"], "IMPOSSIBLE_ACTION_BUDGET")
        self.assertEqual(result["ceiling"], 1)
        self.assertEqual(result["bound"], "current_labor")

    def test_absolute_bound_refuses_false_safe_claim(self):
        result = mod.assess_proposed_expansion(obs(hour=22), 6)
        self.assertEqual(result["verdict"], "NOT_CERTIFIED")
        self.assertEqual(result["ceiling"], 6)

    def test_above_absolute_bound_is_impossible(self):
        result = mod.assess_proposed_expansion(obs(hour=22), 7)
        self.assertEqual(result["verdict"], "IMPOSSIBLE_ACTION_BUDGET")

    def test_zero_proposal_is_not_certified_not_promoted(self):
        result = mod.assess_proposed_expansion(obs(hour=23), 0)
        self.assertEqual(result["verdict"], "NOT_CERTIFIED")

    def test_bool_poison_rejected_for_hour(self):
        with self.assertRaises(mod.CapacityInputError):
            mod.capacity_envelope(obs(hour=True))

    def test_bool_poison_rejected_for_proposal(self):
        with self.assertRaises(mod.CapacityInputError):
            mod.assess_proposed_expansion(obs(), True)

    def test_invalid_player_refused(self):
        o = obs()
        o["player"] = 1
        with self.assertRaises(mod.CapacityInputError):
            mod.capacity_envelope(o)

    def test_nonrectangular_tiles_refused(self):
        o = obs()
        o["farms"][0]["tiles"][0].append(None)
        with self.assertRaises(mod.CapacityInputError):
            mod.capacity_envelope(o)

    def test_out_of_day_hour_refused(self):
        with self.assertRaises(mod.CapacityInputError):
            mod.capacity_envelope(obs(hour=24))

    def test_inputs_not_mutated(self):
        o = obs(hour=7, hands=2)
        before = copy.deepcopy(o)
        mod.assess_proposed_expansion(o, 3)
        self.assertEqual(o, before)

    def test_engine_and_donor_identity_exposed(self):
        r = mod.assess_proposed_expansion(obs(), 1)
        self.assertEqual(r["engine_git_blob"], "3c202c7ee921da239356789e266b694635103fc4")
        self.assertEqual(r["historical_donor_pr"], 9806)


if __name__ == "__main__":
    unittest.main()
