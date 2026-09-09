# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import unittest

import jit_seed_staging as predecessor
from jit_seed_order_rail import (
    EXPECTED_BASE_COMPILER_GIT_BLOB,
    _base_blob,
    _place_seed_order_after_inherited,
    _verify_changed_surface,
    compile_jit_expensive_seed_routes,
)


def empty_route(length: int = 24):
    return [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(length)]


def add_plants(route, step: int, crop: str, quantity: int) -> None:
    rows = [["PLANT", crop] for _ in range(quantity)]
    route[step]["farmer"] = rows[0]
    route[step]["hands"] = rows[1:]


def staged_route(target_market):
    route = empty_route()
    route[2]["market"] = [["BUY_SEED", "MELON", 1]]
    route[4]["market"] = deepcopy(target_market)
    add_plants(route, 5, "MELON", 1)
    return route


def interpreted_fills(market, cash: int):
    costs = {
        "HIRE": 100,
        "BUY_LAND": 600,
        "BUY_ANIMAL": 500,
        "BUY_PRODUCT": 50,
        "BUY_SEED": 80,
    }
    fills = []
    for slot, row in enumerate(market[:10]):
        if not row:
            continue
        cost = costs.get(row[0], 0)
        if row[0] == "BUY_SEED":
            cost *= int(row[2])
        if cash >= cost:
            cash -= cost
            fills.append((slot, tuple(row)))
    return fills, cash


class SourceAndIsolationTests(unittest.TestCase):
    def test_01_exact_predecessor_blob(self):
        actual, error = _base_blob()
        self.assertIsNone(error)
        self.assertEqual(actual, EXPECTED_BASE_COMPILER_GIT_BLOB)

    def test_02_compilation_does_not_patch_predecessor_global(self):
        before = predecessor._place_seed_order
        route = staged_route([["HIRE"], [], ["BUY_ANIMAL", "COW", 1]])
        compile_jit_expensive_seed_routes({"R": route})
        self.assertIs(predecessor._place_seed_order, before)

    def test_03_input_and_result_are_deterministic(self):
        route = staged_route([["HIRE"], [], ["BUY_ANIMAL", "COW", 1]])
        original = deepcopy(route)
        first = compile_jit_expensive_seed_routes({"R": route})
        second = compile_jit_expensive_seed_routes({"R": route})
        self.assertEqual(route, original)
        self.assertEqual(first, second)


class OrderingRegressionTests(unittest.TestCase):
    def test_04_predecessor_advances_seed_into_internal_hole(self):
        route = staged_route([["HIRE"], [], ["BUY_ANIMAL", "COW", 1]])
        staged, report = predecessor.compile_jit_expensive_seed_routes({"R": route})
        self.assertTrue(report["certified"])
        self.assertEqual(
            staged["R"][4]["market"],
            [["HIRE"], ["BUY_SEED", "MELON", 1], ["BUY_ANIMAL", "COW", 1]],
        )

    def test_05_order_rail_appends_after_inherited_rows(self):
        route = staged_route([["HIRE"], [], ["BUY_ANIMAL", "COW", 1]])
        staged, report = compile_jit_expensive_seed_routes({"R": route})
        self.assertTrue(report["certified"])
        self.assertEqual(
            staged["R"][4]["market"],
            [["HIRE"], [], ["BUY_ANIMAL", "COW", 1], ["BUY_SEED", "MELON", 1]],
        )
        self.assertTrue(report["invariants"]["inherited_market_rows_same_index_exact"])
        self.assertTrue(report["invariants"]["staged_orders_after_inherited_live_rows"])

    def test_06_cash_witness_preserves_inherited_fill(self):
        route = staged_route([["HIRE"], [], ["BUY_ANIMAL", "COW", 1]])
        old, _ = predecessor.compile_jit_expensive_seed_routes({"R": route})
        new, _ = compile_jit_expensive_seed_routes({"R": route})
        baseline_fills, _ = interpreted_fills(route[4]["market"], 600)
        old_fills, _ = interpreted_fills(old["R"][4]["market"], 600)
        new_fills, _ = interpreted_fills(new["R"][4]["market"], 600)
        animal = (2, ("BUY_ANIMAL", "COW", 1))
        self.assertIn(animal, baseline_fills)
        self.assertNotIn(animal, old_fills)
        self.assertIn(animal, new_fills)

    def test_07_full_prefix_internal_hole_fails_closed(self):
        market = [["HIRE"], [], ["BUY_ANIMAL", "COW", 1]] + [["HIRE"] for _ in range(7)]
        self.assertEqual(len(market), 10)
        route = staged_route(market)
        staged, report = compile_jit_expensive_seed_routes({"R": route})
        self.assertEqual(staged["R"], route)
        self.assertFalse(report["certified"])
        self.assertEqual(report["reason"], "no_certified_plan")

    def test_08_trailing_active_prefix_blank_is_reused(self):
        market = [["HIRE"] for _ in range(8)] + [[], []]
        route = staged_route(market)
        staged, report = compile_jit_expensive_seed_routes({"R": route})
        self.assertTrue(report["certified"])
        self.assertEqual(staged["R"][4]["market"][8], ["BUY_SEED", "MELON", 1])
        self.assertEqual(staged["R"][4]["market"][9], [])

    def test_09_placement_primitive_never_uses_internal_hole(self):
        action = {"market": [["HIRE"], [], ["BUY_ANIMAL", "COW", 1]]}
        placed, slot = _place_seed_order_after_inherited(action, "MELON", 1, 10)
        self.assertTrue(placed)
        self.assertEqual(slot, 3)
        self.assertEqual(action["market"][1], [])

    def test_10_multiple_crops_remain_after_inherited_rows(self):
        route = empty_route()
        route[2]["market"] = [
            ["BUY_SEED", "MELON", 1],
            ["BUY_SEED", "STRAWBERRY", 1],
        ]
        route[4]["market"] = [["HIRE"], [], ["BUY_ANIMAL", "COW", 1]]
        add_plants(route, 5, "MELON", 1)
        route[5]["hands"].append(["PLANT", "STRAWBERRY"])
        staged, report = compile_jit_expensive_seed_routes({"R": route})
        self.assertTrue(report["certified"])
        self.assertEqual(staged["R"][4]["market"][:3], route[4]["market"])
        self.assertEqual(
            staged["R"][4]["market"][3:],
            [["BUY_SEED", "MELON", 1], ["BUY_SEED", "STRAWBERRY", 1]],
        )


class StandaloneValidationTests(unittest.TestCase):
    def assert_invalid(self, route, *, row_kind: str):
        before = deepcopy(route)
        staged, report = compile_jit_expensive_seed_routes({"R": route})
        self.assertEqual(staged["R"], before)
        self.assertFalse(report["certified"])
        self.assertEqual(report["reason"], "malformed_route_row")
        self.assertEqual(report["rejections"][0]["row_kind"], row_kind)

    def test_11_infinite_seed_quantity_fails_without_escape(self):
        route = empty_route()
        route[2]["market"] = [["BUY_SEED", "MELON", float("inf")]]
        add_plants(route, 5, "MELON", 1)
        self.assert_invalid(route, row_kind="market_quantity")

    def test_12_boolean_seed_quantity_is_not_an_integer_receipt(self):
        route = empty_route()
        route[2]["market"] = [["BUY_SEED", "MELON", True]]
        add_plants(route, 5, "MELON", 1)
        self.assert_invalid(route, row_kind="market_quantity")

    def test_13_short_seed_row_fails_closed(self):
        route = empty_route()
        route[2]["market"] = [["BUY_SEED", "MELON"]]
        add_plants(route, 5, "MELON", 1)
        self.assert_invalid(route, row_kind="market_quantity")

    def test_14_malformed_plant_row_fails_closed(self):
        route = empty_route()
        route[2]["market"] = [["BUY_SEED", "MELON", 1]]
        route[5]["farmer"] = ["PLANT"]
        self.assert_invalid(route, row_kind="plant")

    def test_15_boolean_limits_fail_closed(self):
        route = staged_route([])
        staged, report = compile_jit_expensive_seed_routes({"R": route}, max_orders=True)
        self.assertEqual(staged["R"], route)
        self.assertEqual(report["reason"], "invalid_max_orders")

    def test_16_ambiguous_string_route_labels_fail_closed(self):
        class Label:
            def __init__(self, identity):
                self.identity = identity

            def __hash__(self):
                return hash(self.identity)

            def __eq__(self, other):
                return isinstance(other, Label) and self.identity == other.identity

            def __str__(self):
                return "same"

        left = staged_route([])
        right = deepcopy(left)
        staged, report = compile_jit_expensive_seed_routes(
            {Label("left"): left, Label("right"): right}
        )
        self.assertEqual(len(staged), 2)
        self.assertFalse(report["certified"])
        self.assertEqual(report["reason"], "ambiguous_route_labels")


class ReceiptAttackTests(unittest.TestCase):
    def test_17_postcondition_rejects_unreported_priority_advance(self):
        route = staged_route([["HIRE"], [], ["BUY_ANIMAL", "COW", 1]])
        original = {"R": route}
        staged = deepcopy(original)
        staged["R"][2]["market"][0] = []
        staged["R"][4]["market"][1] = ["BUY_SEED", "MELON", 1]
        report = {
            "plans": [{
                "routes": ["R"],
                "crop": "MELON",
                "anchor_step": 2,
                "anchor_slot": 0,
                "placements": {"R": [{"step": 4, "slot": 1, "quantity": 1}]},
            }]
        }
        exact, detail = _verify_changed_surface(original, staged, report, 10)
        self.assertFalse(exact)
        self.assertEqual(detail["reason"], "placement_precedes_inherited_live_row")

    def test_18_placement_route_must_belong_to_plan_routes(self):
        left = staged_route([])
        right = staged_route([])
        original = {"LEFT": left, "RIGHT": right}
        staged = deepcopy(original)
        staged["LEFT"][2]["market"][0] = []
        staged["RIGHT"][4]["market"].append(["BUY_SEED", "MELON", 1])
        report = {
            "plans": [{
                "routes": ["LEFT"],
                "crop": "MELON",
                "anchor_step": 2,
                "anchor_slot": 0,
                "placements": {
                    "RIGHT": [{"step": 4, "slot": 0, "quantity": 1}],
                },
            }],
        }
        exact, detail = _verify_changed_surface(original, staged, report, 10)
        self.assertFalse(exact)
        self.assertEqual(detail["reason"], "malformed_placement_route")

    def test_19_empty_anchor_cannot_be_rewritten_to_another_order(self):
        route = staged_route([])
        original = {"R": route}
        staged = deepcopy(original)
        staged["R"][2]["market"][0] = ["HIRE"]
        staged["R"][4]["market"].append(["BUY_SEED", "MELON", 1])
        report = {
            "certified": True,
            "plans": [{
                "routes": ["R"],
                "crop": "MELON",
                "anchor_step": 2,
                "anchor_slot": 0,
                "placements": {
                    "R": [{"step": 4, "slot": 0, "quantity": 1}],
                },
            }],
        }
        exact, detail = _verify_changed_surface(original, staged, report, 10)
        self.assertFalse(exact)
        self.assertEqual(detail["reason"], "anchor_result_invalid")

    def test_20_nonmarket_action_drift_is_rejected(self):
        route = staged_route([])
        original = {"R": route}
        staged = deepcopy(original)
        staged["R"][2]["market"][0] = []
        staged["R"][4]["market"].append(["BUY_SEED", "MELON", 1])
        staged["R"][4]["diagnostic"] = "invented"
        report = {
            "certified": True,
            "plans": [{
                "routes": ["R"],
                "crop": "MELON",
                "anchor_step": 2,
                "anchor_slot": 0,
                "placements": {
                    "R": [{"step": 4, "slot": 0, "quantity": 1}],
                },
            }],
        }
        exact, detail = _verify_changed_surface(original, staged, report, 10)
        self.assertFalse(exact)
        self.assertEqual(detail["reason"], "nonmarket_action_surface_drift")

    def test_21_candidate_integration_imports_order_rail(self):
        import titan_capillary

        self.assertEqual(
            titan_capillary.compile_jit_expensive_seed_routes.__module__,
            "jit_seed_order_rail",
        )


if __name__ == "__main__":
    unittest.main()
