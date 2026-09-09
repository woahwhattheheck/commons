# SPDX-License-Identifier: Apache-2.0
"""Engine-shaped regressions for final HIRE/cardinality reconciliation."""
from __future__ import annotations

from copy import deepcopy
import unittest

from hire_cardinality import NO_ORDER, reconcile_hire_cardinality


class FakeMechanics:
    PRODUCTS = ["WHEAT", "CARROT"]

    @staticmethod
    def _fib(n):
        a, b = 1, 1
        for _ in range(n):
            a, b = b, a + b
        return a

    @classmethod
    def _hire_cost(cls, hires_today, multiplier=1):
        return cls._fib(hires_today) * multiplier

    @classmethod
    def apply_hire_only_market(cls, farm, action, limit, multiplier=1):
        """Exact engine HIRE behavior for HIRE/zero-SELL-only test queues."""
        result = deepcopy(farm)
        for order in action.get("market", [])[:limit]:
            if not isinstance(order, list) or not order:
                continue
            if order[0] != "HIRE":
                continue
            cost = cls._hire_cost(result["hires_today"], multiplier)
            if result["money"] < cost:
                continue
            result["money"] -= cost
            result["hires_today"] += 1
            result["hands"].append([4, 4])
        return result


def observation(*, money=6, hires_today=0, hands=0):
    return {
        "player": 0,
        "farms": [{
            "money": money,
            "hires_today": hires_today,
            "hands": [[4, 4] for _ in range(hands)],
        }],
    }


class HireCardinalityTests(unittest.TestCase):
    def reconcile(self, obs, action, **cfg):
        config = {"maxMarketOrdersPerTurn": 10, "farmHandCostMult": 1}
        config.update(cfg)
        return reconcile_hire_cardinality(FakeMechanics, obs, config, action)

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
        before = FakeMechanics.apply_hire_only_market(
            obs["farms"][0], action, limit=10)
        after = FakeMechanics.apply_hire_only_market(
            obs["farms"][0], returned, limit=10)
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
            FakeMechanics.apply_hire_only_market(obs["farms"][0], action, 3),
            FakeMechanics.apply_hire_only_market(obs["farms"][0], returned, 3),
        )

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
            FakeMechanics, {}, {}, action)
        self.assertEqual(returned, action)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "observation_unavailable")


if __name__ == "__main__":
    unittest.main(verbosity=2)
