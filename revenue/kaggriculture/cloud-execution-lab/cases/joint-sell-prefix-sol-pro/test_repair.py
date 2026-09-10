#!/usr/bin/env python3
from __future__ import annotations

import ast
import copy
import importlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repair


def repository_root() -> Path:
    for candidate in (HERE, *HERE.parents):
        if (candidate / repair.SOURCE_REL).is_file():
            return candidate
    raise RuntimeError("repository root not found")


REPO = repository_root()
LAB = REPO / "revenue/kaggriculture/cloud-execution-lab"
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))


def load_candidate() -> tuple[ModuleType, tempfile.TemporaryDirectory[str]]:
    candidate = repair.build(REPO)[2]
    temp = tempfile.TemporaryDirectory(prefix="titan-joint-prefix-")
    path = Path(temp.name) / "frozen_selected_candidate.py"
    path.write_bytes(candidate)
    name = "frozen_selected_joint_prefix_candidate"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        temp.cleanup()
        raise RuntimeError("cannot load candidate module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, temp


def fixture(now: int = 100, shed: dict[str, int] | None = None):
    predecessor = importlib.import_module("frozen_selected")
    m = predecessor.m
    farm = {
        "tiles": [[None] * 10 for _ in range(10)],
        "farmer": [4, 4],
        "hands": [],
        "money": 100_000,
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
    }
    private = {
        "shed": dict(shed or {"MILK": 3, "WOOL": 4}),
        "seeds": {},
        "inventories": [{}],
    }
    obs = {
        "step": now,
        "player": 0,
        "farms": [farm, copy.deepcopy(farm)],
        "private": private,
        "market": {
            "inventory": {product: 10_000 for product in m.PRODUCTS},
            "prices": {
                product: m.market_price(product, 10_000) for product in m.PRODUCTS
            },
        },
        "town": {"unlocked_shops": []},
    }
    route = [
        {"farmer": ["PASS"], "hands": [], "market": []}
        for _ in range(720)
    ]
    base = copy.deepcopy(route[now])
    return obs, route, base


def consumer(module: ModuleType, route, planned=None):
    bot = module.FrozenSelected.__new__(module.FrozenSelected)
    bot.controller = SimpleNamespace(R={"test": route}, cur="test")
    bot.mode = "candidate"
    bot.planned = copy.deepcopy(planned or {})
    bot.pending = {}
    bot.previous = None
    bot.observed_harvests = {}
    bot.diagnostics = {}
    return bot


def profitable_defer(**kwargs):
    item = kwargs["item"]
    quantity = int(kwargs["quantity"])
    now = int(kwargs["now"])
    dates = list(kwargs["dates"])
    gain = {"MILK": 3.0, "WOOL": 2.0}.get(item, 0.0)
    if gain and quantity > 1:
        future = dates[-1]
        plan = ((now, quantity - 1), (future, 1))
    else:
        plan = tuple(kwargs["reference"])
    scenarios = {
        "no_rival": {
            "reference_relative_value": 0.0,
            "relative_value": gain,
        },
        "observed_paired": {
            "reference_relative_value": 0.0,
            "relative_value": gain + 0.5,
        },
        "observed_later_order": {
            "reference_relative_value": 0.0,
            "relative_value": gain + 1.0,
        },
    }
    if dates[-1] > now:
        scenarios["observed_next_turn"] = {
            "reference_relative_value": 0.0,
            "relative_value": gain + 0.25,
        }
    if dates[-1] > now + 2:
        scenarios["observed_before_delayed_batch"] = {
            "reference_relative_value": 0.0,
            "relative_value": gain + 0.75,
        }
    report = {
        "item": item,
        "quantity": quantity,
        "plan": list(plan),
        "reference": list(kwargs["reference"]),
        "worst_relative_gain": gain,
        "feasible": True,
        "forced_feasibility": False,
        "accepted": bool(gain),
        "acceptance_score": gain,
        "scenarios": scenarios,
    }
    return plan, report


class ExactCarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predecessor = importlib.import_module("frozen_selected")
        cls.candidate, cls.temp = load_candidate()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_sources_and_engine_prefix_are_bound(self):
        record = repair.receipt(REPO)
        self.assertEqual(
            record["source"]["git_blob"], repair.EXPECTED_SOURCE_GIT_BLOB
        )
        self.assertEqual(
            record["engine"]["git_blob"], repair.EXPECTED_ENGINE_GIT_BLOB
        )
        self.assertTrue(record["engine"]["raw_prefix_contract"])
        self.assertFalse(record["canonical_mutated"])

    def test_patch_is_reversible_two_hunk_four_replacement_closure(self):
        source, _engine, candidate, patch_text = repair.build(REPO)
        restored = candidate.decode("utf-8")
        for _name, old, new in reversed(repair.REPLACEMENTS):
            restored = restored.replace(new, old, 1)
        self.assertEqual(restored, source.decode("utf-8"))
        self.assertEqual(patch_text.count("@@") // 2, 2)
        self.assertEqual(
            repair.receipt(REPO)["candidate"]["replacement_count"], 4
        )
        ast.parse(candidate.decode("utf-8"))

    def test_helper_matches_raw_prefix_contract(self):
        helper = self.candidate._joint_market_prefix
        config = {"maxMarketOrdersPerTurn": 2}
        queue = [["SELL", "MILK", 1], [], ["HIRE"]]
        self.assertEqual(helper(queue, config), queue[:2])
        self.assertIsNot(helper(queue, config), queue)
        self.assertEqual(helper(tuple(queue), config), [])
        for limit in (0, -1, -99):
            with self.subTest(limit=limit):
                self.assertEqual(
                    helper(queue, {"maxMarketOrdersPerTurn": limit}), queue[:1]
                )
        with self.assertRaises((TypeError, ValueError)):
            helper(queue, {"maxMarketOrdersPerTurn": "bad"})

    def _bound(self, module, obs, route, base, config, end=108):
        farm, private = module.post_units(obs, base, config)
        before = copy.deepcopy((obs, route, base, farm, private))
        result = module.joint_resource_bound(
            obs, config, base, farm, private, route, end
        )
        self.assertEqual((obs, route, base, farm, private), before)
        return result

    def test_current_capped_buy_product_no_longer_disables_joint_bound(self):
        obs, route, base = fixture()
        base["market"] = [[], ["BUY_PRODUCT", "FERTILIZER", 1]]
        config = {"maxMarketOrdersPerTurn": 1}
        self.assertIsNone(
            self._bound(self.predecessor, obs, route, base, config)
        )
        result = self._bound(self.candidate, obs, route, base, config)
        self.assertIsNotNone(result)
        self.assertEqual(result["fixed_cost"], 0)

    def test_future_capped_hire_no_longer_creates_false_underfunding(self):
        obs, route, base = fixture()
        obs["farms"][0]["money"] = 0
        route[103]["market"] = [[], ["HIRE"]]
        config = {"maxMarketOrdersPerTurn": 1}
        self.assertIsNone(
            self._bound(self.predecessor, obs, route, base, config)
        )
        result = self._bound(self.candidate, obs, route, base, config)
        self.assertIsNotNone(result)
        self.assertEqual(result["fixed_cost"], 0)

    def test_capped_animal_arrival_no_longer_fabricates_capacity_failure(self):
        obs, route, base = fixture(shed={"MILK": 45, "WOOL": 45})
        base["market"] = [[], ["BUY_ANIMAL", "COW", 100]]
        config = {"maxMarketOrdersPerTurn": 1}
        self.assertIsNone(
            self._bound(self.predecessor, obs, route, base, config)
        )
        result = self._bound(self.candidate, obs, route, base, config)
        self.assertIsNotNone(result)
        self.assertEqual(result["stock_total_upper"], 90)

    def test_active_unsupported_order_still_declines(self):
        obs, route, base = fixture()
        base["market"] = [["BUY_PRODUCT", "FERTILIZER", 1], ["HIRE"]]
        config = {"maxMarketOrdersPerTurn": 1}
        self.assertIsNone(
            self._bound(self.candidate, obs, route, base, config)
        )

    def test_slot_ledger_ignores_only_the_inert_suffix(self):
        plans = {
            "MILK": ((100, 2), (101, 1)),
            "WOOL": ((100, 3), (101, 1)),
        }
        current = {"MILK": 3, "WOOL": 4}
        shed = {"MILK": 3, "WOOL": 4}
        orders = {
            100: [
                ["SELL", "MILK", 3],
                ["SELL", "WOOL", 4],
                ["PASS"],
            ],
            101: [],
        }
        bound = {"stock_upper": shed}
        full = lambda step: copy.deepcopy(orders.get(step, []))
        active = lambda step: self.candidate._joint_market_prefix(
            copy.deepcopy(orders.get(step, [])),
            {"maxMarketOrdersPerTurn": 2},
        )
        self.assertIsNone(
            self.candidate.joint_queue_ledger(
                plans, current, {}, shed, bound, full, 100, 101, 2
            )
        )
        ledger = self.candidate.joint_queue_ledger(
            plans, current, {}, shed, bound, active, 100, 101, 2
        )
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger[101]["extra_items"], ["MILK", "WOOL"])
        self.assertEqual(ledger[101]["total_slots"], 2)

    def _run_choice(self, module, obs, route, base):
        bot = consumer(module, route)
        with patch.object(module, "optimize_lot", side_effect=profitable_defer):
            out = bot.transform(obs, {"maxMarketOrdersPerTurn": 2}, base)
        return out, bot

    def test_returned_action_witness_single_fallback_becomes_joint(self):
        obs, route, base = fixture()
        base["market"] = [
            ["SELL", "MILK", 3],
            ["SELL", "WOOL", 4],
            ["PASS"],  # interpreter-inert suffix at cap=2
        ]
        original = copy.deepcopy((obs, route, base))

        control_out, control = self._run_choice(
            self.predecessor, obs, route, base
        )
        self.assertEqual(control.diagnostics["chosen"]["item"], "MILK")
        self.assertEqual(control_out["market"][0], ["SELL", "MILK", 2])
        self.assertEqual(control_out["market"][1], ["SELL", "WOOL", 4])
        self.assertEqual(control_out["market"][2], ["PASS"])

        candidate_out, candidate = self._run_choice(
            self.candidate, obs, route, base
        )
        self.assertEqual(
            set(candidate.diagnostics["chosen"]["items"]), {"MILK", "WOOL"}
        )
        self.assertEqual(candidate_out["market"][0], ["SELL", "MILK", 2])
        self.assertEqual(candidate_out["market"][1], ["SELL", "WOOL", 3])
        self.assertEqual(candidate_out["market"][2], ["PASS"])
        self.assertNotEqual(
            control_out["market"][:2], candidate_out["market"][:2]
        )
        self.assertEqual((obs, route, base), original)

    def test_active_prefix_without_suffix_is_behavior_identical(self):
        obs, route, base = fixture()
        base["market"] = [
            ["SELL", "MILK", 3],
            ["SELL", "WOOL", 4],
        ]
        control_out, control = self._run_choice(
            self.predecessor, obs, route, base
        )
        candidate_out, candidate = self._run_choice(
            self.candidate, obs, route, base
        )
        self.assertEqual(control_out, candidate_out)
        self.assertEqual(control.planned, candidate.planned)
        self.assertEqual(control.pending, candidate.pending)

    def test_receipt_is_deterministic_and_json_roundtrippable(self):
        first = repair.receipt(REPO)
        second = repair.receipt(REPO)
        self.assertEqual(first, second)
        self.assertEqual(json.loads(json.dumps(first, sort_keys=True)), first)
        self.assertEqual(first["strength_claim"],
                         "SOURCE_REAL_RETURNED_ACTION_WITNESS_ONLY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
