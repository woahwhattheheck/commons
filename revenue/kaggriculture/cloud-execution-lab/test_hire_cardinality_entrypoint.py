# SPDX-License-Identifier: Apache-2.0
"""Composition contracts for the final HIRE/cardinality boundary."""
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
import sys
import unittest

import main


class FakeFeatures:
    def __init__(self, market_pressure=False, fourth_quadrant=False, **kwargs):
        self.market_pressure = market_pressure
        self.fourth_quadrant = fourth_quadrant
        self.budget_seconds = float(kwargs.get("budget_seconds", 1.0))


class FakeHistory:
    def __init__(self):
        self.remembered = []

    def remember(self, returned):
        self.remembered.append(deepcopy(returned))


class FakeTitanAgent:
    def __init__(self, features, fourth_quadrant_admission=None):
        self.features = features
        self.diagnostics = {}
        self.calls = []
        self.history = FakeHistory()

    def _market_pressure_selected(self, obs, cfg, selected):
        if not self.features.market_pressure:
            return selected
        self.calls.append("pressure")
        result = deepcopy(selected)
        result["trace"] = result.get("trace", []) + ["pressure"]
        return result

    def _feed_stock_selected(self, obs, cfg, selected):
        self.calls.append("feed")
        result = deepcopy(selected)
        result["trace"] = result.get("trace", []) + ["feed"]
        return result

    def _early_capital_selected(self, obs, cfg, selected):
        self.calls.append("capital")
        result = deepcopy(selected)
        result["trace"] = result.get("trace", []) + ["capital"]
        return result

    def _finish_production(self, obs, returned, cfg=None):
        returned = self._feed_stock_selected(obs, cfg or {}, returned)
        returned = self._early_capital_selected(obs, cfg or {}, returned)
        self.history.remember(returned)
        return returned


class HireCardinalityEntrypointTests(unittest.TestCase):
    def make_agent(self, *, pressure=True):
        runtime = ModuleType("titan_runtime")
        runtime.Features = FakeFeatures
        runtime.TitanAgent = FakeTitanAgent
        runtime.load = lambda *args, **kwargs: self.fail("optional admission loaded")

        mechanics = ModuleType("mechanics")
        cardinality = ModuleType("hire_cardinality")
        self.guard_calls = []

        def reconcile(actual_mechanics, obs, cfg, selected):
            self.guard_calls.append((actual_mechanics, obs, cfg, deepcopy(selected)))
            result = deepcopy(selected)
            result["trace"] = result.get("trace", []) + ["cardinality"]
            return result, {"changed": True, "reason": "test_guard"}

        cardinality.reconcile_hire_cardinality = reconcile
        modules = {
            "titan_runtime": runtime,
            "mechanics": mechanics,
            "hire_cardinality": cardinality,
        }
        with patch.dict(sys.modules, modules):
            agent = main._new_instance(Path("."), {
                "market_pressure": pressure,
                "fourth_quadrant": False,
            })
        return agent, modules

    def run_with_modules(self, agent, modules, status):
        agent.diagnostics["status"] = status
        selected = {"farmer": ["PASS"], "hands": [], "market": [], "trace": []}
        with patch.dict(sys.modules, modules):
            return agent._finish_production({"player": 0}, selected, {})

    def test_guard_runs_after_every_completed_transform_before_history(self):
        agent, modules = self.make_agent(pressure=True)
        result = self.run_with_modules(agent, modules, "completed")
        self.assertEqual(result["trace"], [
            "feed", "capital", "pressure", "cardinality",
        ])
        self.assertEqual(agent.calls, ["feed", "capital", "pressure"])
        self.assertEqual(agent.history.remembered, [result])
        self.assertEqual(agent.diagnostics["hire_cardinality"], {
            "changed": True,
            "reason": "test_guard",
        })
        self.assertEqual(len(self.guard_calls), 1)
        self.assertEqual(
            self.guard_calls[0][3]["trace"],
            ["feed", "capital", "pressure"],
        )

    def test_guard_is_independent_of_pressure_feature(self):
        agent, modules = self.make_agent(pressure=False)
        result = self.run_with_modules(agent, modules, "completed")
        self.assertEqual(result["trace"], ["feed", "capital", "cardinality"])
        self.assertEqual(agent.calls, ["feed", "capital"])
        self.assertEqual(len(self.guard_calls), 1)

    def test_deadline_fallback_does_not_start_the_guard(self):
        agent, modules = self.make_agent(pressure=True)
        result = self.run_with_modules(agent, modules, "deadline_fallback")
        self.assertEqual(result["trace"], ["feed", "capital"])
        self.assertEqual(agent.calls, ["feed", "capital"])
        self.assertEqual(self.guard_calls, [])
        self.assertNotIn("hire_cardinality", agent.diagnostics)


if __name__ == "__main__":
    unittest.main(verbosity=2)
