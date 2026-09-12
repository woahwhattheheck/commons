# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
LAB = HERE.parents[4]
DOCS = V3 / "docs"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


materializer = _load(
    "v4_salvage_scheduler_prefix_consumers",
    DOCS / "v4_salvage_scheduler_prefix.py",
)


def _extract_method(candidate: bytes, name: str, namespace: dict):
    tree = ast.parse(candidate.decode("utf-8"))
    classes = [
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SellScheduler"
    ]
    if len(classes) != 1:
        raise AssertionError(f"expected one SellScheduler, got {len(classes)}")
    methods = [
        node for node in classes[0].body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(methods) != 1:
        raise AssertionError(f"expected one {name}, got {len(methods)}")
    module = ast.Module(body=methods, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, f"<scheduler-{name}>", "exec"), namespace)
    return namespace[name]


class _FakeMechanics:
    LAND_ORDER = ("NW", "NE", "SW", "SE")

    @staticmethod
    def _apply_unit_action(farm, private, index, action, tile_count, day, turns, cap):
        return None

    @staticmethod
    def _spawn_hand(farm, index):
        return {"index": index}

    @staticmethod
    def _drop_inventories_to_shed(private, cap):
        return None


class V4SchedulerPrefixConsumerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scheduler = (LAB / "scheduler.py").read_bytes()
        engine = (LAB / "reference" / "engine" / "kaggriculture.py").read_bytes()
        cls.candidate = materializer.materialize_bytes(scheduler, engine)

        def order_spend(order, farm, inventory, params, hires, config):
            if not order:
                return 0, hires
            op = order[0]
            costs = {
                "HIRE": 1000,
                "BUY_LAND": 2000,
                "BUY_SEED": 3000,
                "BUY_ANIMAL": 4000,
                "BUY_PRODUCT": 5000,
            }
            return costs.get(op, 0), hires + (1 if op == "HIRE" else 0)

        cls.parent = SimpleNamespace(PASS={"farmer": ["PASS"], "hands": [], "market": []})
        globals_ns = {
            "copy": copy,
            "m": _FakeMechanics,
            "parent": cls.parent,
            "_order_spend": order_spend,
        }
        cls.cash_reserve = _extract_method(
            cls.candidate, "cash_reserve", dict(globals_ns)
        )
        cls.receipt_profile = _extract_method(
            cls.candidate, "receipt_profile", dict(globals_ns)
        )

    @staticmethod
    def _cash_obs():
        return {
            "step": 0,
            "player": 0,
            "farms": [{
                "unlocked_quadrants": ["NW"],
                "hires_today": 0,
            }],
            "market": {"inventory": {}, "params": {}},
        }

    @staticmethod
    def _scheduler(route=None):
        if route is None:
            route = []
        return SimpleNamespace(
            controller=SimpleNamespace(R=[route], cur=0)
        )

    def test_cash_reserve_excludes_current_capped_suffix_spend(self):
        base = {
            "market": [
                [],
                ["HIRE"],
                ["BUY_LAND"],
                ["BUY_PRODUCT", "WHEAT", 1],
            ]
        }
        obs = self._cash_obs()
        self.assertEqual(
            self.cash_reserve(
                self._scheduler(),
                obs,
                {"maxMarketOrdersPerTurn": 1},
                base,
                0,
            ),
            0,
        )
        self.assertEqual(
            self.cash_reserve(
                self._scheduler(),
                obs,
                {"maxMarketOrdersPerTurn": 2},
                base,
                0,
            ),
            1000,
        )
        self.assertEqual(
            self.cash_reserve(
                self._scheduler(),
                obs,
                {"maxMarketOrdersPerTurn": 4},
                base,
                0,
            ),
            8000,
        )

    def test_cash_reserve_excludes_future_capped_suffix_spend(self):
        route = [
            self.parent.PASS,
            {
                "farmer": ["PASS"],
                "hands": [],
                "market": [[], ["HIRE"], ["BUY_LAND"]],
            },
        ]
        obs = self._cash_obs()
        base = {"market": []}
        self.assertEqual(
            self.cash_reserve(
                self._scheduler(route),
                obs,
                {"maxMarketOrdersPerTurn": 1},
                base,
                1,
            ),
            0,
        )
        self.assertEqual(
            self.cash_reserve(
                self._scheduler(route),
                obs,
                {"maxMarketOrdersPerTurn": 3},
                base,
                1,
            ),
            3000,
        )

    def test_cash_reserve_nonpositive_cap_clamps_to_one_and_nonlist_is_empty(self):
        obs = self._cash_obs()
        active_first = {"market": [["HIRE"], ["BUY_LAND"]]}
        for cap in (-3, -1, 0, 1):
            with self.subTest(cap=cap):
                self.assertEqual(
                    self.cash_reserve(
                        self._scheduler(),
                        obs,
                        {"maxMarketOrdersPerTurn": cap},
                        active_first,
                        0,
                    ),
                    1000,
                )
        for market in (None, {}, "HIRE", (["HIRE"],)):
            with self.subTest(market=market):
                self.assertEqual(
                    self.cash_reserve(
                        self._scheduler(),
                        obs,
                        {"maxMarketOrdersPerTurn": 10},
                        {"market": market},
                        0,
                    ),
                    0,
                )

    def test_receipt_profile_ignores_capped_suffix_buy(self):
        farm = {"tiles": [], "hands": []}
        private = {
            "shed": {"CARROT": 1, "MELON": 98},
            "inventories": [],
        }
        base = {"market": [[], ["BUY_PRODUCT", "WHEAT", 1]]}
        obs = {"step": 0}
        feasible = self.receipt_profile(
            self._scheduler(),
            obs,
            base,
            farm,
            private,
            0,
            "CARROT",
            {"maxMarketOrdersPerTurn": 1, "shedCapacity": 100},
        )
        self.assertTrue(feasible(()))
        included = self.receipt_profile(
            self._scheduler(),
            obs,
            base,
            farm,
            private,
            0,
            "CARROT",
            {"maxMarketOrdersPerTurn": 2, "shedCapacity": 100},
        )
        self.assertFalse(included(()))

    def test_receipt_profile_current_sell_prepass_obeys_same_prefix(self):
        farm = {"tiles": [], "hands": []}
        private = {
            "shed": {"CARROT": 1, "MELON": 99},
            "inventories": [],
        }
        base = {"market": [[], ["SELL", "MELON", 1]]}
        obs = {"step": 0}
        capped = self.receipt_profile(
            self._scheduler(),
            obs,
            base,
            farm,
            private,
            0,
            "CARROT",
            {"maxMarketOrdersPerTurn": 1, "shedCapacity": 100},
        )
        self.assertFalse(capped(()))
        active = self.receipt_profile(
            self._scheduler(),
            obs,
            base,
            farm,
            private,
            0,
            "CARROT",
            {"maxMarketOrdersPerTurn": 2, "shedCapacity": 100},
        )
        self.assertTrue(active(()))

    def test_receipt_profile_nonlist_market_is_inert(self):
        farm = {"tiles": [], "hands": []}
        private = {
            "shed": {"CARROT": 1, "MELON": 98},
            "inventories": [],
        }
        obs = {"step": 0}
        for market in (None, {}, "SELL", (["BUY_PRODUCT", "WHEAT", 1],)):
            with self.subTest(market=market):
                feasible = self.receipt_profile(
                    self._scheduler(),
                    obs,
                    {"market": market},
                    farm,
                    private,
                    0,
                    "CARROT",
                    {"maxMarketOrdersPerTurn": 10, "shedCapacity": 100},
                )
                self.assertTrue(feasible(()))


if __name__ == "__main__":
    unittest.main()
