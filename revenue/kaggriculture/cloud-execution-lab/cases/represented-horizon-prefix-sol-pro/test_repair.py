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
    temp = tempfile.TemporaryDirectory(prefix="titan-represented-horizon-")
    path = Path(temp.name) / "frozen_selected_candidate.py"
    path.write_bytes(candidate)
    name = "frozen_selected_represented_horizon_candidate"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        temp.cleanup()
        raise RuntimeError("cannot load candidate module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, temp


def physical_state(shed: dict[str, int] | None = None):
    farm = {
        "tiles": [[None] * 10 for _ in range(10)],
        "farmer": [4, 4],
        "hands": [],
        "money": 100_000,
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
    }
    private = {
        "shed": dict(shed or {}),
        "seeds": {},
        "inventories": [{}],
    }
    return farm, private


def route_fixture(length: int = 200):
    return [
        {"farmer": ["PASS"], "hands": [], "market": []}
        for _ in range(length)
    ]


def consumer(module: ModuleType, route):
    bot = module.FrozenSelected.__new__(module.FrozenSelected)
    bot.controller = SimpleNamespace(R={"test": route}, cur="test")
    bot.mode = "candidate"
    bot.planned = {}
    bot.pending = {}
    bot.previous = None
    bot.observed_harvests = {}
    bot.diagnostics = {}
    bot.observe = lambda _obs: None
    bot.cash_reserve = lambda *_args, **_kwargs: 0
    bot.receipt_profile = lambda *_args, **_kwargs: (lambda _plan: True)
    bot.rival_supply = lambda *_args, **_kwargs: 0
    return bot


def horizon_optimizer(**kwargs):
    now = int(kwargs["now"])
    dates = [int(t) for t in kwargs["dates"]]
    quantity = int(kwargs["quantity"])
    reference = tuple(tuple(row) for row in kwargs["reference"])
    extended = max(dates) >= now + 2
    plan = ((now, quantity - 1), (now + 2, 1)) if extended else reference
    gain = 1.0 if extended else 0.0
    scenarios = {
        "no_rival": {
            "reference_relative_value": 0.0,
            "relative_value": gain,
        },
        "observed_paired": {
            "reference_relative_value": 0.0,
            "relative_value": gain,
        },
        "observed_later_order": {
            "reference_relative_value": 0.0,
            "relative_value": gain,
        },
    }
    report = {
        "item": kwargs["item"],
        "quantity": quantity,
        "plan": list(plan),
        "reference": list(reference),
        "worst_relative_gain": gain,
        "feasible": True,
        "forced_feasibility": False,
        "accepted": extended,
        "acceptance_score": gain,
        "scenarios": scenarios,
    }
    return plan, report


class RepresentedHorizonPrefixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predecessor = importlib.import_module("frozen_selected")
        cls.candidate, cls.temp = load_candidate()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_source_and_interpreter_are_bound(self):
        record = repair.receipt(REPO)
        self.assertEqual(
            record["source"]["git_blob"], repair.EXPECTED_SOURCE_GIT_BLOB
        )
        self.assertEqual(
            record["engine"]["git_blob"], repair.EXPECTED_ENGINE_GIT_BLOB
        )
        self.assertTrue(record["engine"]["raw_prefix_contract"])
        self.assertFalse(record["canonical_mutated"])

    def test_patch_is_two_replacement_reversible_closure(self):
        source, _engine, candidate, patch_text = repair.build(REPO)
        restored = candidate.decode("utf-8")
        for _name, old, new in reversed(repair.REPLACEMENTS):
            restored = restored.replace(new, old, 1)
        self.assertEqual(restored, source.decode("utf-8"))
        self.assertEqual(
            repair.receipt(REPO)["candidate"]["replacement_count"], 2
        )
        self.assertTrue(patch_text)
        ast.parse(candidate.decode("utf-8"))

    def _event(
        self,
        module: ModuleType,
        *,
        current_market,
        route,
        shed: dict[str, int] | None = None,
        baseline_end: int = 101,
        hard_end: int = 102,
        config: dict | None = None,
    ):
        farm, private = physical_state(shed)
        before = copy.deepcopy((farm, private, route, current_market))
        result = module.represented_shed_event(
            100,
            baseline_end,
            hard_end,
            route,
            farm,
            private,
            dict(config or {"turnsPerDay": 24, "maxMarketOrdersPerTurn": 1}),
            current_market,
        )
        self.assertEqual((farm, private, route, current_market), before)
        return result

    def test_current_capped_buy_cannot_fabricate_drop_event(self):
        route = route_fixture()
        route[101]["farmer"] = ["PICKUP", "FERTILIZER", 1]
        route[102]["farmer"] = ["DROP"]
        authored = [[], ["BUY_PRODUCT", "FERTILIZER", 1]]
        self.assertEqual(
            self._event(self.predecessor, current_market=authored, route=route),
            102,
        )
        self.assertIsNone(
            self._event(self.candidate, current_market=authored, route=route)
        )

    def test_future_capped_buy_cannot_fabricate_drop_event(self):
        route = route_fixture()
        route[101]["market"] = [[], ["BUY_PRODUCT", "FERTILIZER", 1]]
        route[102]["farmer"] = ["PICKUP", "FERTILIZER", 1]
        route[103]["farmer"] = ["DROP"]
        self.assertEqual(
            self._event(
                self.predecessor,
                current_market=[],
                route=route,
                baseline_end=102,
                hard_end=103,
            ),
            103,
        )
        self.assertIsNone(
            self._event(
                self.candidate,
                current_market=[],
                route=route,
                baseline_end=102,
                hard_end=103,
            )
        )

    def test_capped_sell_cannot_erase_real_drop_event(self):
        route = route_fixture()
        route[101]["farmer"] = ["PICKUP", "FERTILIZER", 1]
        route[102]["farmer"] = ["DROP"]
        authored = [[], ["SELL", "FERTILIZER", 1]]
        self.assertIsNone(
            self._event(
                self.predecessor,
                current_market=authored,
                route=route,
                shed={"FERTILIZER": 1},
            )
        )
        self.assertEqual(
            self._event(
                self.candidate,
                current_market=authored,
                route=route,
                shed={"FERTILIZER": 1},
            ),
            102,
        )

    def test_active_prefix_buy_remains_visible(self):
        route = route_fixture()
        route[101]["farmer"] = ["PICKUP", "FERTILIZER", 1]
        route[102]["farmer"] = ["DROP"]
        authored = [["BUY_PRODUCT", "FERTILIZER", 1], ["PASS"]]
        control = self._event(
            self.predecessor, current_market=authored[:1], route=route
        )
        candidate = self._event(
            self.candidate, current_market=authored, route=route
        )
        self.assertEqual(control, 102)
        self.assertEqual(candidate, control)

    def test_nonlist_queue_matches_interpreter_empty_queue(self):
        route = route_fixture()
        route[101]["farmer"] = ["PICKUP", "FERTILIZER", 1]
        route[102]["farmer"] = ["DROP"]
        authored = ([], ["BUY_PRODUCT", "FERTILIZER", 1])
        self.assertEqual(
            self._event(self.predecessor, current_market=authored, route=route),
            102,
        )
        self.assertIsNone(
            self._event(self.candidate, current_market=authored, route=route)
        )

    def test_nonpositive_limit_uses_interpreter_minimum_one(self):
        route = route_fixture()
        route[101]["farmer"] = ["PICKUP", "FERTILIZER", 1]
        route[102]["farmer"] = ["DROP"]
        authored = [
            ["BUY_PRODUCT", "FERTILIZER", 1],
            ["SELL", "FERTILIZER", 1],
        ]
        for limit in (0, -1, -99):
            with self.subTest(limit=limit):
                self.assertIsNone(
                    self._event(
                        self.predecessor,
                        current_market=authored,
                        route=route,
                        config={
                            "turnsPerDay": 24,
                            "maxMarketOrdersPerTurn": limit,
                        },
                    )
                )
                self.assertEqual(
                    self._event(
                        self.candidate,
                        current_market=authored,
                        route=route,
                        config={
                            "turnsPerDay": 24,
                            "maxMarketOrdersPerTurn": limit,
                        },
                    ),
                    102,
                )

    def test_malformed_limit_fails_at_same_conversion_boundary_as_engine(self):
        route = route_fixture()
        farm, private = physical_state()
        with self.assertRaises((TypeError, ValueError)):
            self.candidate.represented_shed_event(
                100,
                101,
                102,
                route,
                farm,
                private,
                {"turnsPerDay": 24, "maxMarketOrdersPerTurn": "bad"},
                [],
            )

    @staticmethod
    def _obs(farm, private, module):
        inventory = {product: 10_000 for product in module.m.PRODUCTS}
        prices = {
            product: module.m.market_price(product, inventory[product])
            for product in module.m.PRODUCTS
        }
        return {
            "step": 100,
            "player": 0,
            "farms": [copy.deepcopy(farm), copy.deepcopy(farm)],
            "private": copy.deepcopy(private),
            "market": {"inventory": inventory, "prices": prices},
            "town": {"unlocked_shops": []},
        }

    def _transform(self, module: ModuleType, *, suffix: bool):
        route = route_fixture()
        route[101]["farmer"] = ["PICKUP", "FERTILIZER", 1]
        route[102]["farmer"] = ["DROP"]
        farm, private = physical_state({"MILK": 2, "FERTILIZER": 0})
        base = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "MILK", 2]],
        }
        if suffix:
            base["market"].append(["BUY_PRODUCT", "FERTILIZER", 1])
        obs = self._obs(farm, private, module)
        bot = consumer(module, route)
        horizon = {
            "baseline_end": 101,
            "hard_end": 102,
            "service_dates": {"MILK": 101},
            "unit_event": None,
            "extended": False,
        }
        with (
            patch.object(
                module,
                "post_units",
                return_value=(copy.deepcopy(farm), copy.deepcopy(private)),
            ),
            patch.object(
                module,
                "event_aware_horizon",
                return_value=(101, copy.deepcopy(horizon)),
            ),
            patch.object(
                module,
                "funded_minimum_now",
                return_value=(0, {"witness": "represented-horizon"}),
            ),
            patch.object(module, "optimize_lot", side_effect=horizon_optimizer),
            patch.object(
                module,
                "fund_same_turn_acquisition",
                side_effect=lambda market, *_args, **_kwargs: (market, None),
            ),
            patch.object(module, "seller_public_observation", return_value={}),
        ):
            out = bot.transform(
                obs,
                {
                    "episodeSteps": 200,
                    "turnsPerDay": 24,
                    "maxMarketOrdersPerTurn": 1,
                },
                copy.deepcopy(base),
            )
        return out, bot, base, obs, route

    def test_returned_action_witness_false_horizon_withholds_active_sale(self):
        control_out, control, base, obs, route = self._transform(
            self.predecessor, suffix=True
        )
        candidate_out, candidate, _base, _obs, _route = self._transform(
            self.candidate, suffix=True
        )

        self.assertEqual(control.diagnostics["horizon"]["unit_event"], 102)
        self.assertIsNone(candidate.diagnostics["horizon"]["unit_event"])
        self.assertEqual(control_out["market"][0], ["SELL", "MILK", 1])
        self.assertEqual(candidate_out["market"][0], ["SELL", "MILK", 2])
        self.assertEqual(
            control_out["market"][1], ["BUY_PRODUCT", "FERTILIZER", 1]
        )
        self.assertEqual(candidate_out["market"][1], base["market"][1])
        self.assertEqual(base["market"][0], ["SELL", "MILK", 2])
        self.assertEqual(obs["private"]["shed"]["MILK"], 2)
        self.assertEqual(route[101]["farmer"], ["PICKUP", "FERTILIZER", 1])

    def test_no_suffix_control_and_candidate_are_identical(self):
        control_out, control, *_ = self._transform(self.predecessor, suffix=False)
        candidate_out, candidate, *_ = self._transform(self.candidate, suffix=False)
        self.assertEqual(control_out, candidate_out)
        self.assertEqual(control.diagnostics["horizon"], candidate.diagnostics["horizon"])
        self.assertEqual(control.planned, candidate.planned)
        self.assertEqual(control.pending, candidate.pending)

    def test_receipt_is_deterministic_and_json_roundtrippable(self):
        first = repair.receipt(REPO)
        second = repair.receipt(REPO)
        self.assertEqual(first, second)
        self.assertEqual(json.loads(json.dumps(first, sort_keys=True)), first)
        self.assertEqual(
            first["strength_claim"], "SOURCE_REAL_RETURNED_ACTION_WITNESS_ONLY"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
