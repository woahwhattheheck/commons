# SPDX-License-Identifier: Apache-2.0
"""Engine-shaped regressions for final HIRE/cardinality reconciliation."""
from __future__ import annotations

from copy import deepcopy
import unittest

import mechanics
from hire_cardinality import NO_ORDER, reconcile_hire_cardinality


def observation(*, money=6, hires_today=0, hands=0):
    return {
        "player": 0,
        "farms": [{
            "money": money,
            "hires_today": hires_today,
            "farmer": [4, 4],
            "hands": [[4, 4] for _ in range(hands)],
        }],
    }


def apply_hire_only_market(farm, action, limit, multiplier=1):
    """Execute the tested queue with the mechanically extracted HIRE primitive."""
    result = deepcopy(farm)
    private = {"inventories": [{} for _ in range(1 + len(result["hands"]))]}
    for order in action.get("market", [])[:limit]:
        if isinstance(order, list) and order and order[0] == "HIRE":
            mechanics._do_hire(result, private, 10, multiplier)
    return result


class HireCardinalityTests(unittest.TestCase):
    def reconcile(self, obs, action, **cfg):
        config = {"maxMarketOrdersPerTurn": 10, "farmHandCostMult": 1}
        config.update(cfg)
        return reconcile_hire_cardinality(mechanics, obs, config, action)

    def test_replay_107130860_fourth_hire_is_replaced_and_transition_is_equal(self):
        obs = observation(money=6, hands=0)
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"]],
        }
        original = deepcopy(action)
        returned, report = self.reconcile(obs, action)

        self.assertEqual(returned["market"], [
            ["HIRE"], ["HIRE"], ["HIRE"], list(NO_ORDER),
        ])
        self.assertEqual(action, original, "caller-owned selected action mutated")
        before = apply_hire_only_market(obs["farms"][0], action, limit=10)
        after = apply_hire_only_market(obs["farms"][0], returned, limit=10)
        self.assertEqual(after, before)
        self.assertEqual(len(after["hands"]), 3)
        self.assertEqual(after["money"], 2)
        self.assertEqual(report["hire_costs"], [1, 1, 2, 3])
        self.assertEqual(report["executable_hires"], 3)
        self.assertEqual(report["cash_blocked_hires"], 1)
        self.assertEqual(report["removed_order_indices"], [3])
        self.assertEqual(report["expected_hands_after_action"], 3)
        self.assertEqual(report["reason"], "impossible_hire_suffix_reconciled")

    def test_following_observation_clips_phantom_worker_suffix(self):
        obs = observation(money=2, hires_today=3, hands=3)
        action = {
            "farmer": ["PASS"],
            "hands": [["NORTH"], ["SOUTH"], ["WATER"], ["EAST"]],
            "market": [],
        }
        returned, report = self.reconcile(obs, action)
        self.assertEqual(returned["hands"], action["hands"][:3])
        self.assertEqual(report["current_hand_actions_clipped"], 1)
        self.assertEqual(report["returned_hand_actions_before"], 4)
        self.assertEqual(report["returned_hand_actions_after"], 3)
        self.assertEqual(report["reason"], "current_hand_cardinality_reconciled")

    def test_existing_daily_hires_use_the_exact_next_fibonacci_cost(self):
        obs = observation(money=2, hires_today=2)
        action = {"hands": [], "market": [["HIRE"], ["HIRE"]]}
        returned, report = self.reconcile(obs, action)
        self.assertEqual(returned["market"], [["HIRE"], list(NO_ORDER)])
        self.assertEqual(report["hire_costs"], [2, 3])
        self.assertEqual(report["executable_hires"], 1)
        self.assertEqual(report["cash_after_executable_hires"], 0)

    def test_market_order_limit_replaces_only_the_ignored_hire_suffix(self):
        obs = observation(money=100)
        action = {"hands": [], "market": [["HIRE"] for _ in range(4)]}
        returned, report = self.reconcile(
            obs, action, maxMarketOrdersPerTurn=3)
        self.assertEqual(returned["market"], [
            ["HIRE"], ["HIRE"], ["HIRE"], list(NO_ORDER),
        ])
        self.assertEqual(report["order_limit_blocked_hires"], 1)
        self.assertEqual(report["executable_hires"], 3)
        self.assertEqual(report["removed_order_indices"], [3])
        self.assertEqual(
            apply_hire_only_market(obs["farms"][0], action, 3),
            apply_hire_only_market(obs["farms"][0], returned, 3),
        )

    def test_zero_quantity_sell_is_a_proved_noop_before_hire(self):
        obs = observation(money=1)
        action = {"hands": [], "market": [list(NO_ORDER), ["HIRE"]]}
        returned, report = self.reconcile(obs, action)
        self.assertEqual(returned, action)
        self.assertTrue(report["market_guard_applied"])
        self.assertEqual(report["hire_costs"], [1])
        self.assertEqual(report["executable_hires"], 1)

    def test_fully_funded_queue_is_byte_shape_unchanged(self):
        obs = observation(money=7, hands=2)
        action = {
            "farmer": ["PASS"],
            "hands": [["PASS"], ["WATER"]],
            "market": [["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"]],
        }
        returned, report = self.reconcile(obs, action)
        self.assertEqual(returned, action)
        self.assertFalse(report["changed"])
        self.assertEqual(report["executable_hires"], 4)
        self.assertEqual(report["reason"], "already_executable")

    def test_active_market_prefix_fails_closed_but_still_clips_current_hands(self):
        obs = observation(money=0, hands=1)
        action = {
            "hands": [["PASS"], ["WATER"]],
            # The sale may fund the later HIRE; the guard must not speculate.
            "market": [["SELL", "WHEAT", 1], ["HIRE"]],
        }
        returned, report = self.reconcile(obs, action)
        self.assertEqual(returned["market"], action["market"])
        self.assertEqual(returned["hands"], [["PASS"]])
        self.assertFalse(report["market_guard_applied"])
        self.assertEqual(report["current_hand_actions_clipped"], 1)
        self.assertEqual(report["reason"], "current_hand_cardinality_only")

    def test_missing_observation_fails_closed(self):
        action = {"hands": [["PASS"]], "market": [["HIRE"]]}
        returned, report = reconcile_hire_cardinality(
            mechanics, {}, {}, action)
        self.assertEqual(returned, action)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "observation_unavailable")


if __name__ == "__main__":
    unittest.main(verbosity=2)
