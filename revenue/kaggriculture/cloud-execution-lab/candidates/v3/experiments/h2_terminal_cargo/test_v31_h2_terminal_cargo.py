# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_full_router as r04  # noqa: E402
import r04_h2_terminal_cargo as h2  # noqa: E402


def observation(step, farmer=(0, 0), hands=(), inventories=None):
    size = 10
    tiles = [[None for _ in range(size)] for _ in range(size)]
    farm = {
        "tiles": tiles,
        "farmer": list(farmer),
        "hands": [list(position) for position in hands],
        "money": 1000,
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    if inventories is None:
        inventories = [{"MILK": 3}] + [{} for _ in hands]
    self_private = {
        "inventories": [dict(item) for item in inventories],
        "shed": {},
    }
    prices = {product: 10 for product in r04.PRODUCTS}
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [farm, copy.deepcopy(farm)],
        "private": self_private,
        "market": {"prices": prices, "inventory": {}},
        "town": {"unlocked_shops": []},
    }


def action(farmer=("PASS",), hands=(), market=None):
    return {
        "farmer": list(farmer),
        "hands": [list(command) for command in hands],
        "market": copy.deepcopy(market or [["SELL", "WOOL", 2]]),
    }


class TerminalCargoReturnTests(unittest.TestCase):
    def run_candidate(self, act, obs, enabled=True, first_step=696):
        return h2.protect_terminal_cargo(
            act, obs, enabled=enabled, first_step=first_step)

    def test_flag_off_is_exact_object_identity(self):
        act = action(("MOVE", "S"))
        obs = observation(716, farmer=(4, 2))
        out, changed, units = self.run_candidate(act, obs, enabled=False)
        self.assertIs(out, act)
        self.assertEqual((changed, units), (0, 0))

    def test_before_first_step_is_exact_identity(self):
        act = action(("MOVE", "S"))
        obs = observation(695, farmer=(4, 2))
        out, changed, units = self.run_candidate(act, obs)
        self.assertIs(out, act)
        self.assertEqual((changed, units), (0, 0))

    def test_more_than_one_turn_slack_is_unchanged(self):
        # Shed access includes (4,4); from (4,3) distance=1. At step715
        # three turns remain, so H2 still has >1 turn of schedule slack.
        act = action(("CARE",))
        obs = observation(715, farmer=(4, 3))
        out, changed, units = self.run_candidate(act, obs)
        self.assertIs(out, act)
        self.assertEqual((changed, units), (0, 0))

    def test_deadline_routes_one_step_toward_nearest_shed(self):
        # At step716 two turns remain. Distance=1 plus one turn of slack
        # reaches the trigger boundary.
        act = action(("CARE",), market=[["SELL", "MILK", 1]])
        obs = observation(716, farmer=(4, 3), inventories=[{"MILK": 3}])
        out, changed, units = self.run_candidate(act, obs)
        target = h2._nearest_shed_cell((4, 3), obs["farms"][0]["tiles"])
        self.assertEqual(out["farmer"], r04._v219_walk((4, 3), target))
        self.assertEqual((changed, units), (1, 3))
        self.assertEqual(out["market"], act["market"])
        self.assertEqual(act["farmer"], ["CARE"])

    def test_exact_last_chance_route_is_allowed(self):
        # Distance=2 at step716 and two turns remain: moves on 716 and 717
        # put the worker on a shed cell for unchanged step718 liquidation.
        act = action(("CARE",))
        obs = observation(716, farmer=(4, 2))
        out, changed, units = self.run_candidate(act, obs)
        target = h2._nearest_shed_cell((4, 2), obs["farms"][0]["tiles"])
        self.assertEqual(out["farmer"], r04._v219_walk((4, 2), target))
        self.assertEqual((changed, units), (1, 3))

    def test_impossible_return_does_not_sacrifice_final_work(self):
        act = action(("HARVEST",))
        obs = observation(717, farmer=(0, 0))
        out, changed, units = self.run_candidate(act, obs)
        self.assertIs(out, act)
        self.assertEqual((changed, units), (0, 0))

    def test_home_worker_is_pinned_if_parent_would_leave(self):
        act = action(("MOVE", "N"))
        obs = observation(717, farmer=(4, 4), inventories=[{"WOOL": 5}])
        out, changed, units = self.run_candidate(act, obs)
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertEqual((changed, units), (1, 5))
        self.assertEqual(out["market"], act["market"])

    def test_home_pass_is_already_safe_and_keeps_identity(self):
        act = action(("PASS",))
        obs = observation(717, farmer=(4, 4), inventories=[{"WOOL": 5}])
        out, changed, units = self.run_candidate(act, obs)
        self.assertIs(out, act)
        self.assertEqual((changed, units), (0, 0))

    def test_existing_drop_or_place_is_preserved(self):
        for command in (("DROP",), ("PLACE", "MILK", 2)):
            with self.subTest(command=command):
                act = action(command)
                obs = observation(717, farmer=(4, 4), inventories=[{"MILK": 3}])
                out, changed, units = self.run_candidate(act, obs)
                self.assertIs(out, act)
                self.assertEqual((changed, units), (0, 0))

    def test_non_product_cargo_does_not_activate(self):
        act = action(("MOVE", "N"))
        obs = observation(717, farmer=(4, 4), inventories=[{"COW": 1}])
        out, changed, units = self.run_candidate(act, obs)
        self.assertIs(out, act)
        self.assertEqual((changed, units), (0, 0))

    def test_last_step_is_owned_by_parent_liquidation(self):
        act = action(("MOVE", "N"))
        obs = observation(r04.LAST_STEP, farmer=(4, 4), inventories=[{"MILK": 3}])
        out, changed, units = self.run_candidate(act, obs)
        self.assertIs(out, act)
        self.assertEqual((changed, units), (0, 0))

    def test_hand_override_preserves_farmer_and_market(self):
        act = action(("PASS",), hands=(("CARE",),),
                     market=[["SELL", "STRAWBERRY", 7], ["HIRE"]])
        obs = observation(
            716,
            farmer=(4, 4),
            hands=((4, 3),),
            inventories=[{}, {"STRAWBERRY": 4}],
        )
        out, changed, units = self.run_candidate(act, obs)
        target = h2._nearest_shed_cell((4, 3), obs["farms"][0]["tiles"])
        self.assertEqual(out["hands"][0], r04._v219_walk((4, 3), target))
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertEqual(out["market"], act["market"])
        self.assertEqual((changed, units), (1, 4))

    def test_invalid_first_step_fails_closed(self):
        with self.assertRaises(ValueError):
            self.run_candidate(action(), observation(716), first_step=-1)


if __name__ == "__main__":
    unittest.main()
