# SPDX-License-Identifier: Apache-2.0
"""Exact current runtime and preserved official-engine contracts."""
from copy import deepcopy
import hashlib
import importlib.util
import inspect
import os
import sys
from types import ModuleType, SimpleNamespace
import unittest

from seed_prefix_test_support import LAB, _Budget, _proposal, _selected, prefix


EXACT_SOURCE_PRESENT = (
    (LAB / "titan_runtime.py").is_file()
    and (LAB / "reference" / "engine" / "kaggriculture.py").is_file()
)
if os.environ.get("TITAN_REQUIRE_EXACT_SOURCE") == "1" and not EXACT_SOURCE_PRESENT:
    raise RuntimeError("exact repository source required but unavailable")


@unittest.skipUnless(EXACT_SOURCE_PRESENT, "exact repository source not present")
class ExactCurrentIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import titan_runtime

        cls.runtime = titan_runtime
        cls.seed_funding = titan_runtime.load(
            "_titan_prefix_test_seed_funding",
            LAB / "reference" / "titan-current" / "seed_funding.py",
        )

    @staticmethod
    def _action_pair(active=False):
        market = (
            [["BUY_SEED", "WHEAT", 2], ["HIRE"], *([[]] * 9)]
            if active
            else [["BUY_SEED", "WHEAT", 2], *([[]] * 9), ["HIRE"]]
        )
        baseline = _selected(market)
        return baseline, _proposal(baseline, {0: []})

    def _runtime_agent(self, proposed):
        farm = {
            "money": 10.0,
            "hires_today": 0,
            "unlocked_quadrants": ["NW"],
            "farmer": [4, 4],
            "hands": [],
            "tiles": [[None] * 10 for _ in range(10)],
        }
        private = {
            "seeds": {
                "WHEAT": 0,
                "CARROT": 0,
                "TOMATO": 0,
                "STRAWBERRY": 0,
                "MELON": 0,
            },
            "shed": {},
            "inventories": [{}],
        }
        agent = self.runtime.TitanAgent(
            self.runtime.Features(seed=True, funding=True)
        )
        agent.consumer = SimpleNamespace(selected_post_units=(farm, private))
        agent.controller = SimpleNamespace(cur="MAIN")
        agent.spatial = None
        agent.seed_budget = _Budget(proposed)
        agent.funding_module = self.seed_funding
        agent.diagnostics = {}
        obs = {
            "step": 600,
            "player": 0,
            "farms": [deepcopy(farm), deepcopy(farm)],
            "private": deepcopy(private),
            "market": {"inventory": {}},
        }
        return agent, obs

    def test_exact_current_method_source_binding(self):
        observed = hashlib.sha256(
            inspect.getsource(
                self.runtime.TitanAgent._seed_selected
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(observed, prefix.EXPECTED_SEED_SELECTED_SHA256)

    def test_predecessor_falls_back_but_candidate_releases_tail_only_edit(self):
        baseline, proposed = self._action_pair()
        predecessor, obs = self._runtime_agent(proposed)
        control = predecessor._seed_selected(
            deepcopy(obs), {"maxMarketOrdersPerTurn": 10}, deepcopy(baseline)
        )
        self.assertEqual(control, baseline)
        self.assertEqual(
            predecessor.diagnostics["seed_funding"]["reason"],
            "original_queue_needs_additional_cash",
        )

        candidate, obs = self._runtime_agent(proposed)
        installed = prefix.install_seed_prefix_dependency(candidate)
        self.assertEqual(installed["status"], "installed")
        result = candidate._seed_selected(
            deepcopy(obs), {"maxMarketOrdersPerTurn": 10}, deepcopy(baseline)
        )
        self.assertEqual(result, proposed)
        self.assertEqual(
            candidate.diagnostics["seed_prefix_dependency"]["status"],
            "inactive_tail_only",
        )

    def test_exact_current_active_dependency_remains_fail_closed(self):
        baseline, proposed = self._action_pair(active=True)
        candidate, obs = self._runtime_agent(proposed)
        prefix.install_seed_prefix_dependency(candidate)
        result = candidate._seed_selected(
            deepcopy(obs), {"maxMarketOrdersPerTurn": 10}, deepcopy(baseline)
        )
        self.assertEqual(result, baseline)
        self.assertEqual(
            candidate.diagnostics["seed_prefix_dependency"]["reason"],
            "executable_downstream_capital_dependency",
        )

    @staticmethod
    def _load_engine():
        package = sys.modules.get("kaggle_environments")
        utils = sys.modules.get("kaggle_environments.utils")
        if package is None:
            package = ModuleType("kaggle_environments")
            package.__path__ = []
            sys.modules["kaggle_environments"] = package
        if utils is None:
            utils = ModuleType("kaggle_environments.utils")
            utils.resolve_episode_seed = lambda _env: 0
            sys.modules["kaggle_environments.utils"] = utils
        spec = importlib.util.spec_from_file_location(
            "_titan_prefix_official_engine",
            LAB / "reference" / "engine" / "kaggriculture.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _run_market(engine, action, max_orders=10):
        farms = [engine._new_farm(10, 3000), engine._new_farm(10, 3000)]
        farms[0]["money"] = 10.0
        private = [engine._new_private(), engine._new_private()]
        market = engine._new_market()
        observations = [
            SimpleNamespace(market=market, farms=farms, private=private[0]),
            SimpleNamespace(market=market, farms=farms, private=private[1]),
        ]
        state = [
            SimpleNamespace(action=deepcopy(action), observation=observations[0]),
            SimpleNamespace(action={"market": []}, observation=observations[1]),
        ]
        env = SimpleNamespace(
            configuration={
                "boardSize": 10,
                "maxMarketOrdersPerTurn": max_orders,
                "farmHandCostMult": 1,
                "shedCapacity": 100,
            }
        )
        engine._process_market(state, env)
        return farms[0], private[0]

    def test_official_engine_ignores_tail_and_candidate_avoids_seed_spend(self):
        engine = self._load_engine()
        baseline, proposed = self._action_pair()
        base_farm, base_private = self._run_market(engine, baseline, 10)
        new_farm, new_private = self._run_market(engine, proposed, 10)

        # Order 10 is outside the ten-row active queue in both actions.
        self.assertEqual(base_farm["hands"], [])
        self.assertEqual(new_farm["hands"], [])
        # The predecessor spends the only $10 on one unnecessary seed; the
        # demand-valid proposal preserves it.  This is exact engine execution,
        # not an estimated score or future-value claim.
        self.assertEqual(base_farm["money"], 0.0)
        self.assertEqual(new_farm["money"], 10.0)
        self.assertEqual(base_private["seeds"]["WHEAT"], 1)
        self.assertEqual(new_private["seeds"]["WHEAT"], 0)


if __name__ == "__main__":
    unittest.main()
