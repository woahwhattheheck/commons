#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

LAB = Path(__file__).resolve().parent
COMPOSER = LAB / "candidates/v4/repairs/scheduler-action-prefix/compose_current_native.py"

spec = importlib.util.spec_from_file_location("v5_prefix_composer", COMPOSER)
current = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(current)


def function_from(source: str, name: str, namespace=None):
    start, end = current._span(source, name)
    ns = {} if namespace is None else dict(namespace)
    exec(compile(source[start:end], f"<{name}>", "exec"), ns)
    return ns[name]


def quantities(orders):
    result = {}
    for order in orders:
        if order and len(order) > 2 and order[0] == "SELL":
            result[order[1]] = result.get(order[1], 0) + max(0, int(order[2]))
    return result


class FrozenSelectedExecutablePrefixV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (LAB / "frozen_selected.py").read_text()
        compile(cls.source, "<frozen-selected-v5>", "exec")
        if cls.source.count("scheduling._engine_market_prefix") != 4:
            raise AssertionError("expected four canonical scheduler-prefix consumers")

    def test_materialize_preserves_nonexecuted_suffix(self):
        fn = function_from(self.source, "materialize_sales")
        orders = [[], ["SELL", "MILK", 4]]
        self.assertEqual(
            fn(orders, {"MILK": 0}, {"MILK": 4}, {"MILK"}, 1),
            orders,
        )

    def test_same_turn_funding_ignores_nonexecuted_suffix_target_and_source(self):
        def prefix_state(orders, _farm, _private, _market, _shops, _config, _now,
                         _rival_quantity, stop):
            outcomes = {}
            money = 0
            for index, order in enumerate(orders[:max(0, int(stop) + 1)]):
                if order != ["HIRE"]:
                    continue
                funded = any(
                    row and len(row) > 2 and row[:2] == ["SELL", "WOOL"]
                    and int(row[2]) > 0
                    for row in orders[:index]
                )
                outcomes[index] = {
                    "required": 1,
                    "completed": int(funded),
                    "cost_per_unit": 10,
                }
                if funded:
                    money = 190
            return {
                "money": money,
                "outcomes": outcomes,
                "unsupported_index": None,
                "sale_stress": [],
            }

        fn = function_from(
            self.source,
            "fund_same_turn_acquisition",
            {
                "copy": copy,
                "_market_prefix_state": prefix_state,
                "sale_quantities": quantities,
            },
        )
        farm = {"money": 0}
        private = {"shed": {"WOOL": 1}}
        market = {"inventory": {"WOOL": 10000}}
        config = {"maxMarketOrdersPerTurn": 10}
        targets = {"WOOL": 1}

        tail_target = [[] for _ in range(10)] + [["HIRE"], ["SELL", "WOOL", 1]]
        target, target_info = fn(
            tail_target, farm, private, market, [], config, 0, targets,
            lambda _product: 0,
        )
        self.assertEqual(target, tail_target)
        self.assertIsNone(target_info)

        tail_source = [[] for _ in range(9)] + [["HIRE"], ["SELL", "WOOL", 1]]
        source, source_info = fn(
            tail_source, farm, private, market, [], config, 0, targets,
            lambda _product: 0,
        )
        self.assertEqual(source, tail_source)
        self.assertEqual(source_info["reason"], "no-safe-prefix-sale")

    def test_represented_market_uses_list_only_engine_prefix_and_minimum_one(self):
        fn = function_from(self.source, "apply_represented_market")

        private = {"shed": {"MILK": 4}}
        fn({"hands": []}, private, [[], ["SELL", "MILK", 4]], 10, 1)
        self.assertEqual(private["shed"]["MILK"], 4)

        private = {"shed": {"MILK": 4}}
        fn({"hands": []}, private, (["SELL", "MILK", 4],), 10, 1)
        self.assertEqual(private["shed"]["MILK"], 4)

        for raw_cap in (0, -3):
            with self.subTest(max_orders=raw_cap):
                private = {"shed": {"MILK": 4}}
                fn(
                    {"hands": []},
                    private,
                    [["SELL", "MILK", 1], ["SELL", "MILK", 3]],
                    10,
                    raw_cap,
                )
                self.assertEqual(private["shed"]["MILK"], 3)

    def test_joint_queue_accepts_preserved_raw_suffix(self):
        materialize = function_from(self.source, "materialize_sales")
        fn = function_from(
            self.source,
            "joint_queue_ledger",
            {
                "PRODUCTS": {"MILK"},
                "sale_quantities": quantities,
                "materialize_sales": materialize,
                "shared_slot_ledger": lambda plans, orders_at, cap: {
                    "plans": plans,
                    "cap": cap,
                },
            },
        )
        orders_at = lambda _t: [[], ["SELL", "MILK", 1]]
        result = fn(
            {"MILK": [(0, 0)]}, {"MILK": 0}, {}, {"MILK": 1},
            {"stock_upper": {"MILK": 1}}, orders_at, 0, 0, 1,
        )
        self.assertIsNotNone(result)

    def test_horizon_does_not_treat_suffix_sell_as_executable(self):
        fn = function_from(
            self.source,
            "event_aware_horizon",
            {
                "parent": SimpleNamespace(DECISIONS=[]),
                "absorption": lambda *args, **kwargs: True,
                "HORIZON": 1,
            },
        )
        route = [{"market": []} for _ in range(6)]
        for step in range(2, 6):
            route[step] = {"market": [["HIRE"], ["SELL", "MILK", 1]]}
        end, report = fn(0, 5, route, {"MILK": 1}, [], {"maxMarketOrdersPerTurn": 1})
        self.assertEqual(report["service_dates"], {})
        self.assertEqual(end, 1)

    def test_all_local_cap_consumers_use_minimum_one(self):
        for name in ("materialize_sales", "_funding_trace", "fund_same_turn_acquisition",
                     "joint_resource_bound", "joint_queue_ledger", "event_aware_horizon",
                     "apply_represented_market"):
            start, end = current._span(self.source, name)
            fragment = self.source[start:end]
            if "maxMarketOrdersPerTurn" in fragment or name in {
                "materialize_sales", "joint_queue_ledger", "apply_represented_market"
            }:
                self.assertIn("max(1,int(", fragment.replace(" ", ""), name)


if __name__ == "__main__":
    unittest.main()
