# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from types import SimpleNamespace
import sys
import unittest

from candidate_runtime import apply_completed_action


CROPS = {
    "WHEAT": {"seed": 10},
    "CARROT": {"seed": 20},
    "TOMATO": {"seed": 50},
    "STRAWBERRY": {"seed": 100},
    "MELON": {"seed": 80},
}


class Budget:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def remaining(self, crop, step, route):
        self.calls.append((crop, step, route))
        return self.values.get(crop, 0)


class Instance:
    def __init__(self, post, *, values=None, spatial=None, status="completed"):
        self.diagnostics = {"status": status}
        self.features = SimpleNamespace(consumer="frozen", terminal_route=False)
        self.controller = SimpleNamespace(cur="route-a")
        self.seed_budget = Budget(values or {"MELON": 5})
        self.spatial = spatial
        self.post = post

    def _selected_snapshot(self, observation, selected):
        return self.post


class CandidateRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.previous = sys.modules.get("scheduler")
        sys.modules["scheduler"] = SimpleNamespace(
            m=SimpleNamespace(CROPS=CROPS),
            post_units=lambda *_args: (_ for _ in ()).throw(AssertionError("unexpected fallback")),
        )
        self.obs = {"step": 9, "player": 0}
        self.cfg = {"maxMarketOrdersPerTurn": 10}
        self.post = {
            "farms": [{"money": 3000}, {"money": 3000}],
            "private": {"seeds": {crop: 0 for crop in CROPS}},
        }
        self.action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["BUY_SEED", "MELON", 4], ["BUY_SEED", "MELON", 4]],
        }

    def tearDown(self):
        if self.previous is None:
            sys.modules.pop("scheduler", None)
        else:
            sys.modules["scheduler"] = self.previous

    def test_binds_completed_snapshot_route_and_step(self):
        instance = Instance(deepcopy(self.post))
        result, report = apply_completed_action(instance, self.obs, self.cfg, self.action)
        self.assertEqual(result["market"][1], ["BUY_SEED", "MELON", 1])
        self.assertTrue(report["changed"])
        self.assertEqual(report["snapshot_source"], "completed_snapshot")
        self.assertEqual(report["route"], "route-a")
        self.assertEqual(report["step"], 9)
        self.assertIn(("MELON", 9, "route-a"), instance.seed_budget.calls)

    def test_spatial_future_request_is_added_conservatively(self):
        spatial = SimpleNamespace(future_seed_requests=lambda step: {"MELON": 3})
        instance = Instance(deepcopy(self.post), spatial=spatial)
        result, report = apply_completed_action(instance, self.obs, self.cfg, self.action)
        self.assertIs(result, self.action)
        self.assertEqual(report["reason"], "within_aggregate_bound")
        self.assertEqual(report["demand_deficit"], 8)

    def test_incomplete_parent_is_identity_decline(self):
        instance = Instance(deepcopy(self.post), status="deadline_fallback")
        result, report = apply_completed_action(instance, self.obs, self.cfg, self.action)
        self.assertIs(result, self.action)
        self.assertEqual(report["reason"], "parent_not_completed")

    def test_uses_canonical_post_unit_fallback(self):
        post_private = deepcopy(self.post["private"])
        post_farm = {"money": 3000}
        sys.modules["scheduler"].post_units = lambda *_args: (post_farm, post_private)
        instance = Instance(None)
        result, report = apply_completed_action(instance, self.obs, self.cfg, self.action)
        self.assertTrue(report["changed"])
        self.assertEqual(report["snapshot_source"], "canonical_post_units")
        self.assertEqual(result["market"][1][2], 1)

    def test_malformed_spatial_demand_fails_closed(self):
        spatial = SimpleNamespace(future_seed_requests=lambda step: {"MELON": True})
        instance = Instance(deepcopy(self.post), spatial=spatial)
        result, report = apply_completed_action(instance, self.obs, self.cfg, self.action)
        self.assertIs(result, self.action)
        self.assertEqual(report["reason"], "invalid_spatial_demand")

    def test_day_hour_input_is_normalized_before_snapshot(self):
        seen = {}
        instance = Instance(deepcopy(self.post))
        def snapshot(observation, selected):
            seen.update(observation)
            return instance.post
        instance._selected_snapshot = snapshot
        obs = {"day": 1, "hour": 2, "player": 0}
        result, report = apply_completed_action(instance, obs, {"turnsPerDay": 24}, self.action)
        self.assertTrue(report["changed"])
        self.assertEqual(report["step"], 26)
        self.assertEqual(seen["step"], 26)

    def test_out_of_range_player_fails_closed(self):
        instance = Instance(deepcopy(self.post))
        result, report = apply_completed_action(instance, {"step": 9, "player": -1}, self.cfg, self.action)
        self.assertIs(result, self.action)
        self.assertEqual(report["reason"], "invalid_player")

    def test_terminal_route_is_unsupported(self):
        instance = Instance(deepcopy(self.post))
        instance.features.terminal_route = True
        result, report = apply_completed_action(instance, self.obs, self.cfg, self.action)
        self.assertIs(result, self.action)
        self.assertEqual(report["reason"], "unsupported_parent_mode")


if __name__ == "__main__":
    unittest.main()
