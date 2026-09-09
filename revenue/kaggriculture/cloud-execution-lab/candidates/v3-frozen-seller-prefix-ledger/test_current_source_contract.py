# SPDX-License-Identifier: Apache-2.0
"""Predecessor-discriminating current-source and pinned-engine contracts."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import prefix_ledger


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CurrentFrozenSelectedContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen = load("_prefix_contract_frozen", LAB / "frozen_selected.py")

    def _consumer(self):
        consumer = object.__new__(self.frozen.FrozenSelected)
        consumer.mode = "naive"
        consumer.planned = {"CARROT": [(11, 4)]}
        consumer.pending = {}
        consumer.previous = None
        consumer.observed_harvests = {}
        consumer.diagnostics = {}
        consumer.controller = SimpleNamespace(cur=0, R=[[{
            "farmer": ["PASS"], "hands": [], "market": []
        } for _ in range(20)]])
        consumer.cash_reserve = lambda *_args, **_kwargs: 0
        return consumer

    def test_exact_current_method_erases_plan_for_inactive_tail(self):
        consumer = self._consumer()
        base = {
            "farmer": ["PASS"], "hands": [],
            "market": [[] for _ in range(10)] + [["SELL", "CARROT", 4]],
        }
        farm = {"money": 3000, "tiles": [[None] * 10 for _ in range(10)],
                "farmer": [4, 4], "hands": [], "unlocked_quadrants": ["NW"],
                "hires_today": 0}
        private = {"shed": {product: (4 if product == "CARROT" else 0)
                            for product in self.frozen.m.PRODUCTS},
                   "seeds": {crop: 0 for crop in self.frozen.m.CROPS},
                   "inventories": [{}]}
        obs = {"step": 10, "player": 0, "farms": [farm, deepcopy(farm)],
               "private": private,
               "market": {"inventory": {p: 10000 for p in self.frozen.m.PRODUCTS},
                           "prices": {p: 1 for p in self.frozen.m.PRODUCTS}},
               "town": {"unlocked_shops": []}}
        cfg = {"episodeSteps": 720, "turnsPerDay": 24,
               "maxMarketOrdersPerTurn": 10}
        horizon = {"baseline_end": 10, "hard_end": 10, "service_dates": {},
                   "unit_event": None, "extended": False}
        with patch.object(self.frozen, "post_units", return_value=(farm, private)), \
             patch.object(self.frozen, "event_aware_horizon", return_value=(10, horizon)), \
             patch.object(self.frozen, "represented_shed_event", return_value=None), \
             patch.object(self.frozen, "fund_same_turn_acquisition",
                          side_effect=lambda orders, *_a, **_k: (orders, None)):
            returned = self.frozen.FrozenSelected.transform(consumer, obs, cfg, base)
        self.assertEqual(returned, base)
        self.assertEqual(consumer.pending["CARROT"], 0)
        self.assertNotIn("CARROT", consumer.planned)

        planned, pending, report = prefix_ledger.reconcile_prefix_ledger(
            planned_before={"CARROT": [(11, 4)]},
            planned_after=consumer.planned,
            pending_after=consumer.pending,
            diagnostics=consumer.diagnostics,
            shed=private["shed"], market=returned["market"], step=10, max_orders=10,
        )
        self.assertTrue(report["changed"])
        self.assertEqual(pending["CARROT"], 4)
        self.assertEqual(planned["CARROT"], [(11, 4)])


class OfficialEnginePrefixContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.engine = load("_prefix_contract_engine",
                              LAB / "reference/engine/kaggriculture.py")
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest(f"pinned kaggle dependency unavailable: {exc}")

    def _state(self, first_action):
        e = self.engine
        farms = [e._new_farm(10, 3000), e._new_farm(10, 3000)]
        privates = [e._new_private(), e._new_private()]
        privates[0]["shed"]["CARROT"] = 4
        market = e._new_market()
        observations = [
            SimpleNamespace(farms=farms, market=market, private=privates[i])
            for i in range(2)
        ]
        states = [
            SimpleNamespace(action=first_action, observation=observations[0]),
            SimpleNamespace(action={"market": []}, observation=observations[1]),
        ]
        env = SimpleNamespace(configuration={"boardSize": 10,
                                             "maxMarketOrdersPerTurn": 10,
                                             "farmHandCostMult": 1,
                                             "shedCapacity": 100})
        return states, env, farms, privates

    def test_official_engine_ignores_suffix_sale_and_executes_active_sale(self):
        tail = {"market": [[] for _ in range(10)] + [["SELL", "CARROT", 4]]}
        states, env, farms, privates = self._state(tail)
        self.engine._process_market(states, env)
        self.assertEqual(privates[0]["shed"]["CARROT"], 4)
        self.assertEqual(farms[0]["money"], 3000)

        active = {"market": [["SELL", "CARROT", 4]]}
        states, env, farms, privates = self._state(active)
        self.engine._process_market(states, env)
        self.assertEqual(privates[0]["shed"]["CARROT"], 0)
        self.assertGreater(farms[0]["money"], 3000)


if __name__ == "__main__":
    unittest.main()
