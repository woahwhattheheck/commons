# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

import apply_rebind as carrier

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
MAIN = ROOT / carrier.TARGET
PRESSURE_DIR = ROOT / "revenue/kaggriculture/cloud-opponent-league/lark-responsive"


def load_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def quote(item, inventory, _params):
    if item == "FERTILIZER":
        return 10 if inventory == 100 else 1
    if item == "CARROT":
        return 5
    return 2


class Features:
    def __init__(self, **values):
        self.__dict__.update(values)


class RuntimeBase:
    pressure = None

    def __init__(self, features=None, *, fourth_quadrant_admission=None):
        self.features = features
        self.spatial = None
        self.diagnostics = {"status": "completed"}

    def _early_capital_selected(self, _obs, _cfg, selected):
        return selected

    def _market_pressure_selected(self, obs, cfg, selected):
        return self.pressure.transform(selected, obs, cfg, quote=quote)


def load_main(source: bytes, pressure):
    fake = types.ModuleType("titan_runtime")
    RuntimeBase.pressure = pressure
    fake.TitanAgent = RuntimeBase
    fake.Features = Features
    fake.load = lambda *_args, **_kwargs: None
    previous = sys.modules.get("titan_runtime")
    sys.modules["titan_runtime"] = fake
    try:
        module = types.ModuleType("_rebind_main_under_test")
        module.__file__ = str(MAIN)
        exec(compile(source, str(MAIN), "exec"), module.__dict__)
        agent = module._new_instance(Path(tempfile.gettempdir()),
                                    {"fourth_quadrant": False})
    finally:
        if previous is None:
            sys.modules.pop("titan_runtime", None)
        else:
            sys.modules["titan_runtime"] = previous
    return agent


class FinalPressureFertilizerRebindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MAIN.read_bytes()
        cls.patched = carrier.patch_bytes(cls.source)
        prior_sell = sys.modules.get("sell_priority")
        try:
            load_path("sell_priority", PRESSURE_DIR / "sell_priority.py")
            cls.pressure = load_path("_pressure_priority_rebind_test",
                                     PRESSURE_DIR / "pressure_priority.py")
        finally:
            if prior_sell is None:
                sys.modules.pop("sell_priority", None)
            else:
                sys.modules["sell_priority"] = prior_sell

    def observation(self):
        return {
            "step": 715,
            "market": {
                "prices": {"CARROT": 5, "FERTILIZER": 10},
                "inventory": {"CARROT": 100, "FERTILIZER": 100},
                "params": {},
            },
        }

    def action(self):
        return {
            "farmer": ["DROP"],
            "hands": [],
            "market": [
                ["SELL", "CARROT", 1],
                ["SELL", "FERTILIZER", 1],
            ],
        }

    def test_exact_source_and_patch_closure(self):
        self.assertEqual(carrier.git_blob_sha1(self.source),
                         carrier.EXPECTED_MAIN_GIT_BLOB_SHA1)
        self.assertNotEqual(self.source, self.patched)
        self.assertEqual(self.patched.decode().count(carrier.NEW), 1)
        compile(self.patched, str(MAIN), "exec")

    def test_actual_pressure_moves_fertilizer_before_carrot(self):
        result = self.pressure.transform(
            self.action(), self.observation(),
            {"maxMarketOrdersPerTurn": 10}, quote=quote)
        self.assertEqual(result["market"][0], ["SELL", "FERTILIZER", 1])
        self.assertEqual(result["market"][1], ["SELL", "CARROT", 1])

    def test_predecessor_returns_executed_sale_but_loses_ledger(self):
        agent = load_main(self.source, self.pressure)
        proposal = {"step": 715, "slot": 1, "worker": 0}
        agent.spatial = types.SimpleNamespace(_sale_proposal=proposal)
        returned = agent._early_capital_selected(
            self.observation(), {"maxMarketOrdersPerTurn": 10}, self.action())
        self.assertEqual(returned["market"][0], ["SELL", "FERTILIZER", 1])
        self.assertEqual(proposal["slot"], 1)
        self.assertNotEqual(returned["market"][proposal["slot"]],
                            ["SELL", "FERTILIZER", 1])

    def test_repair_binds_exact_final_returned_slot(self):
        agent = load_main(self.patched, self.pressure)
        proposal = {"step": 715, "slot": 1, "worker": 0}
        agent.spatial = types.SimpleNamespace(_sale_proposal=proposal)
        returned = agent._early_capital_selected(
            self.observation(), {"maxMarketOrdersPerTurn": 10}, self.action())
        self.assertEqual(returned["market"][0], ["SELL", "FERTILIZER", 1])
        self.assertEqual(proposal["slot"], 0)
        self.assertEqual(returned["market"][proposal["slot"]],
                         ["SELL", "FERTILIZER", 1])
        self.assertEqual(returned["farmer"], ["DROP"])

    def test_no_proposal_preserves_returned_object(self):
        agent = load_main(self.patched, self.pressure)
        agent.spatial = types.SimpleNamespace(_sale_proposal=None)
        action = self.action()
        pressured = RuntimeBase._market_pressure_selected(
            agent, self.observation(), {"maxMarketOrdersPerTurn": 10}, action)
        returned = agent._rebind_idle_fertilizer_sale(self.observation(), pressured)
        self.assertIs(returned, pressured)

    def test_duplicate_fertilizer_cancels_drop_without_mutating_input(self):
        agent = load_main(self.patched, self.pressure)
        agent.spatial = types.SimpleNamespace(
            _sale_proposal={"step": 715, "slot": 0, "worker": 1})
        action = {
            "farmer": ["PASS"],
            "hands": [["DROP"]],
            "market": [
                ["SELL", "FERTILIZER", 1],
                ["SELL", "FERTILIZER", 1],
            ],
        }
        frozen = copy.deepcopy(action)
        returned = agent._rebind_idle_fertilizer_sale(self.observation(), action)
        self.assertEqual(action, frozen)
        self.assertEqual(returned["hands"], [["PASS"]])
        self.assertEqual(returned["market"], [[], []])

    def test_missing_fertilizer_cancels_farmer_drop(self):
        agent = load_main(self.patched, self.pressure)
        agent.spatial = types.SimpleNamespace(
            _sale_proposal={"step": 715, "slot": 0, "worker": 0})
        action = {"farmer": ["DROP"], "hands": [],
                  "market": [["SELL", "CARROT", 1]]}
        returned = agent._rebind_idle_fertilizer_sale(self.observation(), action)
        self.assertEqual(returned["farmer"], ["PASS"])
        self.assertEqual(returned["market"], action["market"])

    def test_wrong_step_is_exact_identity(self):
        agent = load_main(self.patched, self.pressure)
        agent.spatial = types.SimpleNamespace(
            _sale_proposal={"step": 714, "slot": 1, "worker": 0})
        action = self.action()
        returned = agent._rebind_idle_fertilizer_sale(self.observation(), action)
        self.assertIs(returned, action)

    def test_deadline_fallback_does_not_start_late_pressure(self):
        agent = load_main(self.patched, self.pressure)
        proposal = {"step": 715, "slot": 1, "worker": 0}
        agent.spatial = types.SimpleNamespace(_sale_proposal=proposal)
        agent.diagnostics = {"status": "deadline_fallback"}
        action = self.action()
        returned = agent._early_capital_selected(
            self.observation(), {"maxMarketOrdersPerTurn": 10}, action)
        self.assertIs(returned, action)
        self.assertEqual(proposal["slot"], 1)


if __name__ == "__main__":
    unittest.main()
