# SPDX-License-Identifier: Apache-2.0
"""Exact-source predecessor and official-engine witnesses.

These tests run against the repository's pinned production scheduler and engine.
They skip only when this candidate directory is tested outside the repository
checkout; the hosted workflow asserts both pinned files exist before discovery.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import types
import unittest

from market_prefix_guard import preserves_scheduler_contract


HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
SCHEDULER = LAB / "scheduler.py"
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"
CONFIG = {"shedCapacity": 3, "maxMarketOrdersPerTurn": 10}
SHED = {"CARROT": 1, "EGG": 1, "MILK": 1}
BASELINE_MARKET = [
    ["SELL", "CARROT", 1],
    ["BUY_PRODUCT", "WHEAT", 1],
    ["SELL", "EGG", 1],
    ["SELL", "MILK", 1],
]
CANDIDATE_MARKET = [
    [],
    ["BUY_PRODUCT", "WHEAT", 1],
    ["SELL", "EGG", 1],
    ["SELL", "MILK", 1],
]


def _load_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CurrentSchedulerPredecessorTest(unittest.TestCase):
    def test_receipt_profile_accepts_purchase_blocking_plan(self):
        if not SCHEDULER.is_file():
            self.skipTest("repository scheduler.py is not present")
        sys.path.insert(0, str(LAB))
        try:
            scheduler = _load_from_path("sol_ledger_current_scheduler", SCHEDULER)
        finally:
            sys.path.pop(0)

        farm = {"farmer": [0, 0], "hands": [], "tiles": [[None]], "money": 10_000}
        private = {
            "shed": deepcopy(SHED),
            "seeds": {},
            "inventories": [{}],
        }
        obs = {
            "step": 0,
            "player": 0,
            "farms": [deepcopy(farm), deepcopy(farm)],
            "private": deepcopy(private),
        }
        base = {"farmer": ["PASS"], "hands": [], "market": deepcopy(BASELINE_MARKET)}
        instance = object.__new__(scheduler.SellScheduler)
        instance.controller = types.SimpleNamespace(R=[[{}]], cur=0)

        original = scheduler.post_units
        scheduler.post_units = lambda *_args, **_kwargs: (deepcopy(farm), deepcopy(private))
        try:
            feasible = instance.receipt_profile(
                obs,
                base,
                farm,
                private,
                0,
                "CARROT",
                CONFIG,
            )
        finally:
            scheduler.post_units = original

        self.assertTrue(
            feasible(((0, 0),)),
            "the pinned predecessor aggregates the whole row and certifies the unsafe plan",
        )
        safe, report = preserves_scheduler_contract(
            BASELINE_MARKET, CANDIDATE_MARKET, CONFIG
        )
        self.assertFalse(safe)
        self.assertEqual(report["reason"], "PURCHASE_PREFIX_CHANGED")


class OfficialEngineWitnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ENGINE.is_file():
            raise unittest.SkipTest("repository pinned engine is not present")

        package = types.ModuleType("kaggle_environments")
        package.__path__ = []
        utils = types.ModuleType("kaggle_environments.utils")
        utils.resolve_episode_seed = lambda *_args, **_kwargs: 0
        package.utils = utils
        cls._old_package = sys.modules.get("kaggle_environments")
        cls._old_utils = sys.modules.get("kaggle_environments.utils")
        sys.modules["kaggle_environments"] = package
        sys.modules["kaggle_environments.utils"] = utils
        cls.engine = _load_from_path("sol_ledger_pinned_engine", ENGINE)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "_old_package", None) is None:
            sys.modules.pop("kaggle_environments", None)
        else:
            sys.modules["kaggle_environments"] = cls._old_package
        if getattr(cls, "_old_utils", None) is None:
            sys.modules.pop("kaggle_environments.utils", None)
        else:
            sys.modules["kaggle_environments.utils"] = cls._old_utils

    def _run_market(self, market_rows):
        engine = self.engine
        inventory = {item: 10_000 for item in engine.PRODUCTS}
        market = {
            "inventory": inventory,
            "prices": {
                item: engine.market_price(item, inventory[item])
                for item in engine.PRODUCTS
            },
        }
        farms = [
            {"money": 10_000, "hires_today": 0, "hands": [], "unlocked_quadrants": ["NW"]},
            {"money": 10_000, "hires_today": 0, "hands": [], "unlocked_quadrants": ["NW"]},
        ]
        private0 = {"shed": deepcopy(SHED), "seeds": {}, "inventories": [{}]}
        private1 = {"shed": {}, "seeds": {}, "inventories": [{}]}
        obs0 = types.SimpleNamespace(market=market, farms=farms, private=private0)
        obs1 = types.SimpleNamespace(market=market, farms=farms, private=private1)
        state = [
            types.SimpleNamespace(
                action={"farmer": ["PASS"], "hands": [], "market": deepcopy(market_rows)},
                observation=obs0,
            ),
            types.SimpleNamespace(
                action={"farmer": ["PASS"], "hands": [], "market": []},
                observation=obs1,
            ),
        ]
        env = types.SimpleNamespace(
            configuration={
                "boardSize": 10,
                "shedCapacity": CONFIG["shedCapacity"],
                "maxMarketOrdersPerTurn": CONFIG["maxMarketOrdersPerTurn"],
                "farmHandCostMult": 1,
            }
        )
        engine._process_market(state, env)
        return deepcopy(private0["shed"]), farms[0]["money"]

    def test_literal_order_index_changes_inherited_purchase_commit(self):
        baseline_shed, _ = self._run_market(BASELINE_MARKET)
        candidate_shed, _ = self._run_market(CANDIDATE_MARKET)
        self.assertEqual(baseline_shed, {"WHEAT": 1})
        self.assertEqual(candidate_shed, {"CARROT": 1})
        self.assertEqual(baseline_shed.get("WHEAT", 0), 1)
        self.assertEqual(candidate_shed.get("WHEAT", 0), 0)


if __name__ == "__main__":
    unittest.main()
