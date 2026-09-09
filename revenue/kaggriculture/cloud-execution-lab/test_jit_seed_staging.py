# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import json
import unittest

from jit_seed_staging import compile_jit_expensive_seed_routes


def empty_route(length=24):
    return [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(length)]


def add_plants(route, step, crop, quantity):
    rows = [["PLANT", crop] for _ in range(quantity)]
    route[step]["farmer"] = rows[0]
    route[step]["hands"] = rows[1:]


def seed_total(route, crop, max_orders=10):
    return sum(
        int(row[2])
        for action in route
        for row in action["market"][:max_orders]
        if row and len(row) >= 3 and row[:2] == ["BUY_SEED", crop]
    )


def simulate_seed_stock(route, crop, max_orders=10):
    stock = peak = misses = purchases = 0
    for action in route:
        plants = sum(
            1
            for unit in [action["farmer"], *action["hands"]]
            if len(unit) >= 2 and unit[:2] == ["PLANT", crop]
        )
        fulfilled = min(stock, plants)
        misses += plants - fulfilled
        stock -= fulfilled
        for row in action["market"][:max_orders]:
            if row and len(row) >= 3 and row[:2] == ["BUY_SEED", crop]:
                quantity = max(0, int(row[2]))
                stock += quantity
                purchases += quantity
        peak = max(peak, stock)
    return misses, purchases, stock, peak


def minimized_replay_107130860():
    """Exact day-zero market/plant seam from player 1; irrelevant moves removed."""
    route = empty_route()
    markets = {
        1: [["BUY_PRODUCT", "WHEAT", 13]],
        2: [
            ["SELL", "WHEAT", 9],
            ["BUY_SEED", "WHEAT", 7],
            ["BUY_SEED", "MELON", 12],
            ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
            ["BUY_ANIMAL", "COW", 2],
            ["BUY_ANIMAL", "SHEEP", 2],
        ],
        4: [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "WHEAT", 1]],
        5: [["BUY_PRODUCT", "WHEAT", 1]],
        6: [["SELL", "WHEAT", 2], ["BUY_PRODUCT", "WHEAT", 1]],
        7: [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "WHEAT", 1]],
        8: [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "WHEAT", 1]],
        9: [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "WHEAT", 1]],
        10: [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "WHEAT", 1]],
        11: [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "WHEAT", 1]],
        12: [["BUY_PRODUCT", "WHEAT", 1]],
    }
    for step, market in markets.items():
        route[step]["market"] = deepcopy(market)
    for step, quantity in {5: 1, 7: 1, 8: 1, 10: 2, 13: 2, 14: 1,
                           16: 2, 17: 1, 20: 1}.items():
        add_plants(route, step, "MELON", quantity)
    return route


class ReplayCertificateTests(unittest.TestCase):
    def setUp(self):
        self.original = minimized_replay_107130860()
        self.staged, self.report = compile_jit_expensive_seed_routes(
            {"BRYCE": self.original}
        )
        self.route = self.staged["BRYCE"]

    def test_01_admitted(self):
        self.assertTrue(self.report["certified"])
        self.assertEqual(self.report["reason"], "staged")

    def test_02_exact_changed_steps(self):
        self.assertEqual(
            self.report["changed_steps"]["BRYCE"],
            [2, 4, 6, 7, 9, 12, 13, 15, 16, 19],
        )

    def test_03_bulk_row_emptied_in_place(self):
        self.assertEqual(self.route[2]["market"][2], [])
        self.assertEqual(self.route[2]["market"][3:], self.original[2]["market"][3:])

    def test_04_exact_jit_targets(self):
        expected = {4: 1, 6: 1, 7: 1, 9: 2, 12: 2, 13: 1, 15: 2, 16: 1, 19: 1}
        observed = {}
        for step, action in enumerate(self.route):
            for row in action["market"][:10]:
                if row and row[:2] == ["BUY_SEED", "MELON"]:
                    observed[step] = observed.get(step, 0) + int(row[2])
        self.assertEqual(observed, expected)

    def test_05_execution_and_peak_inventory(self):
        baseline = simulate_seed_stock(self.original, "MELON")
        candidate = simulate_seed_stock(self.route, "MELON")
        self.assertEqual(baseline, (0, 12, 0, 12))
        self.assertEqual(candidate, (0, 12, 0, 2))

    def test_06_actor_surface_exact(self):
        self.assertEqual(
            [(x["farmer"], x["hands"]) for x in self.route],
            [(x["farmer"], x["hands"]) for x in self.original],
        )

    def test_07_non_target_rows_preserved(self):
        for step, before in enumerate(self.original):
            for slot, row in enumerate(before["market"]):
                if row and row[:2] == ["BUY_SEED", "MELON"]:
                    continue
                self.assertEqual(self.route[step]["market"][slot], row)

    def test_08_input_report_deterministic(self):
        before = deepcopy(self.original)
        again, report = compile_jit_expensive_seed_routes({"BRYCE": self.original})
        self.assertEqual(self.original, before)
        self.assertEqual(again, self.staged)
        self.assertEqual(report, self.report)
        json.dumps(report, sort_keys=True)


class BasicBehaviorTests(unittest.TestCase):
    def test_09_cheap_wheat_untouched(self):
        route = empty_route()
        route[2]["market"] = [["BUY_SEED", "WHEAT", 2]]
        add_plants(route, 5, "WHEAT", 2)
        self.assertEqual(compile_jit_expensive_seed_routes({"R": route})[0]["R"], route)

    def test_10_unlisted_crop_untouched(self):
        route = empty_route()
        route[2]["market"] = [["BUY_SEED", "PUMPKIN", 2]]
        add_plants(route, 5, "PUMPKIN", 2)
        self.assertEqual(compile_jit_expensive_seed_routes({"R": route})[0]["R"], route)

    def test_11_strawberry_supported(self):
        route = empty_route()
        route[2]["market"] = [["BUY_SEED", "STRAWBERRY", 3]]
        add_plants(route, 5, "STRAWBERRY", 1)
        add_plants(route, 8, "STRAWBERRY", 2)
        staged, report = compile_jit_expensive_seed_routes({"R": route})
        self.assertTrue(report["certified"])
        self.assertEqual(staged["R"][4]["market"], [["BUY_SEED", "STRAWBERRY", 1]])
        self.assertEqual(staged["R"][7]["market"], [["BUY_SEED", "STRAWBERRY", 2]])

    def test_12_next_turn_demand_retained_at_anchor(self):
        route = empty_route()
        route[2]["market"] = [["BUY_SEED", "MELON", 5]]
        add_plants(route, 3, "MELON", 2)
        add_plants(route, 5, "MELON", 3)
        staged, _ = compile_jit_expensive_seed_routes({"R": route})
        self.assertEqual(staged["R"][2]["market"][0], ["BUY_SEED", "MELON", 2])
        self.assertEqual(staged["R"][4]["market"][0], ["BUY_SEED", "MELON", 3])

    def test_13_existing_blank_slot_reserved_without_shift(self):
        route = empty_route()
        route[2]["market"] = [["BUY_SEED", "MELON", 1]]
        add_plants(route, 5, "MELON", 1)
        route[4]["market"] = [["HIRE"], [], ["BUY_ANIMAL", "COW", 1]]
        staged, _ = compile_jit_expensive_seed_routes({"R": route})
        self.assertEqual(
            staged["R"][4]["market"],
            [["HIRE"], ["BUY_SEED", "MELON", 1], ["BUY_ANIMAL", "COW", 1]],
        )

    def test_14_append_reserves_active_slot(self):
        route = empty_route()
        route[2]["market"] = [["BUY_SEED", "MELON", 1]]
        add_plants(route, 5, "MELON", 1)
        route[4]["market"] = [["HIRE"], ["BUY_ANIMAL", "COW", 1]]
        staged, _ = compile_jit_expensive_seed_routes({"R": route})
        self.assertEqual(staged["R"][4]["market"][-1], ["BUY_SEED", "MELON", 1])

    def test_15_inactive_tail_exact(self):
        route = empty_route()
        route[2]["market"] = (
            [["HIRE"], ["BUY_SEED", "MELON", 1]]
            + [["HIRE"] for _ in range(8)]
            + [["BUY_ANIMAL", "SHEEP", 7], ["SELL", "WHEAT", 99]]
        )
        add_plants(route, 5, "MELON", 1)
        tail = deepcopy(route[2]["market"][10:])
        staged, report = compile_jit_expensive_seed_routes({"R": route})
        self.assertTrue(report["certified"])
        self.assertEqual(staged["R"][2]["market"][10:], tail)

    def test_16_two_expensive_crops_share_capacity(self):
        route = empty_route()
        route[2]["market"] = [
            ["BUY_SEED", "MELON", 1],
            ["BUY_SEED", "STRAWBERRY", 1],
        ]
        add_plants(route, 5, "MELON", 1)
        route[5]["hands"].append(["PLANT", "STRAWBERRY"])
        staged, report = compile_jit_expensive_seed_routes({"R": route})
        self.assertTrue(report["certified"])
        self.assertEqual(seed_total(staged["R"], "MELON"), 1)
        self.assertEqual(seed_total(staged["R"], "STRAWBERRY"), 1)


def rejection_case(kind):
    route = empty_route(48 if kind == "cross_day" else 24)
    if kind == "same_turn":
        route[2]["market"] = [["BUY_SEED", "MELON", 1]]
        add_plants(route, 2, "MELON", 1)
    elif kind == "before_anchor":
        add_plants(route, 1, "MELON", 1)
        route[2]["market"] = [["BUY_SEED", "MELON", 2]]
        add_plants(route, 5, "MELON", 1)
    elif kind == "quantity_high":
        route[2]["market"] = [["BUY_SEED", "MELON", 3]]
        add_plants(route, 5, "MELON", 2)
    elif kind == "quantity_low":
        route[2]["market"] = [["BUY_SEED", "MELON", 1]]
        add_plants(route, 5, "MELON", 2)
    elif kind == "multiple_rows":
        route[2]["market"] = [["BUY_SEED", "MELON", 1], ["BUY_SEED", "MELON", 1]]
        add_plants(route, 5, "MELON", 2)
    elif kind == "full_prefix":
        route[2]["market"] = [["BUY_SEED", "MELON", 1]]
        route[4]["market"] = [["HIRE"] for _ in range(10)]
        add_plants(route, 5, "MELON", 1)
    elif kind == "inactive_only":
        route[2]["market"] = [["HIRE"] for _ in range(10)] + [["BUY_SEED", "MELON", 1]]
        add_plants(route, 5, "MELON", 1)
    elif kind == "zero_quantity":
        route[2]["market"] = [["BUY_SEED", "MELON", 0]]
        add_plants(route, 5, "MELON", 1)
    elif kind == "no_plant":
        route[2]["market"] = [["BUY_SEED", "MELON", 1]]
    elif kind == "cross_day":
        route[23]["market"] = [["BUY_SEED", "MELON", 1]]
        add_plants(route, 24, "MELON", 1)
    return route


class RejectionMatrixTests(unittest.TestCase):
    pass


def _install_rejection_test(number, kind):
    def test(self):
        route = rejection_case(kind)
        staged, report = compile_jit_expensive_seed_routes(
            {"R": route}, first_day_only=(kind != "cross_day")
        )
        self.assertEqual(staged["R"], route)
        self.assertFalse(report["certified"])
    test.__name__ = f"test_{number:02d}_{kind}_fails_closed"
    setattr(RejectionMatrixTests, test.__name__, test)


for _number, _kind in enumerate(
    ["same_turn", "before_anchor", "quantity_high", "quantity_low",
     "multiple_rows", "full_prefix", "inactive_only", "zero_quantity",
     "no_plant", "cross_day"],
    start=17,
):
    _install_rejection_test(_number, _kind)


class BranchSafetyTests(unittest.TestCase):
    def test_27_identical_compatible_obligation_stages_all(self):
        left = empty_route()
        left[2]["market"] = [["BUY_SEED", "MELON", 2]]
        add_plants(left, 5, "MELON", 1)
        add_plants(left, 8, "MELON", 1)
        right = deepcopy(left)
        left[10]["farmer"], right[10]["farmer"] = ["WEST"], ["EAST"]
        staged, report = compile_jit_expensive_seed_routes({"LEFT": left, "RIGHT": right})
        self.assertTrue(report["certified"])
        self.assertEqual(report["changed_routes"], ["LEFT", "RIGHT"])

    def test_28_compatible_routes_disagree_fail_closed(self):
        left = empty_route()
        left[2]["market"] = [["BUY_SEED", "MELON", 1]]
        add_plants(left, 5, "MELON", 1)
        right = deepcopy(left)
        right[5] = {"farmer": ["PASS"], "hands": [], "market": []}
        add_plants(right, 6, "MELON", 1)
        staged, report = compile_jit_expensive_seed_routes({"LEFT": left, "RIGHT": right})
        self.assertEqual(staged, {"LEFT": left, "RIGHT": right})
        self.assertFalse(report["certified"])

    def test_29_prediverged_routes_stage_independently(self):
        left, right = empty_route(), empty_route()
        left[0]["farmer"], right[0]["farmer"] = ["WEST"], ["EAST"]
        for route in (left, right):
            route[2]["market"] = [["BUY_SEED", "MELON", 1]]
            add_plants(route, 5, "MELON", 1)
        staged, report = compile_jit_expensive_seed_routes({"LEFT": left, "RIGHT": right})
        self.assertTrue(report["certified"])
        self.assertEqual(staged["LEFT"][4]["market"], [["BUY_SEED", "MELON", 1]])
        self.assertEqual(staged["RIGHT"][4]["market"], [["BUY_SEED", "MELON", 1]])

    def test_30_group_capacity_failure_atomic(self):
        left, right = empty_route(), empty_route()
        for route in (left, right):
            route[2]["market"] = [["BUY_SEED", "MELON", 1]]
            add_plants(route, 5, "MELON", 1)
        left[3]["farmer"], right[3]["farmer"] = ["WEST"], ["EAST"]
        right[4]["market"] = [["HIRE"] for _ in range(10)]
        staged, report = compile_jit_expensive_seed_routes({"LEFT": left, "RIGHT": right})
        self.assertEqual(staged, {"LEFT": left, "RIGHT": right})
        self.assertFalse(report["changed"])

    def test_31_pairwise_branch_topology_exact(self):
        routes = {}
        for name, direction in (("A", "WEST"), ("B", "EAST"), ("C", "NORTH")):
            route = empty_route()
            route[2]["market"] = [["BUY_SEED", "MELON", 1]]
            add_plants(route, 5, "MELON", 1)
            route[10]["farmer"] = [direction]
            routes[name] = route
        _, report = compile_jit_expensive_seed_routes(routes)
        self.assertTrue(report["certified"])
        self.assertTrue(report["invariants"]["branch_topology_exact"])


class InputValidationTests(unittest.TestCase):
    def test_32_empty_routes(self):
        staged, report = compile_jit_expensive_seed_routes({})
        self.assertEqual(staged, {})
        self.assertEqual(report["reason"], "empty_or_non_mapping_routes")

    def test_33_invalid_max_orders(self):
        route = empty_route()
        staged, report = compile_jit_expensive_seed_routes({"R": route}, max_orders=0)
        self.assertEqual(staged["R"], route)
        self.assertEqual(report["reason"], "invalid_max_orders")

    def test_34_invalid_turns_per_day(self):
        route = empty_route()
        staged, report = compile_jit_expensive_seed_routes({"R": route}, turns_per_day=1)
        self.assertEqual(staged["R"], route)
        self.assertEqual(report["reason"], "invalid_turns_per_day")

    def test_35_malformed_route(self):
        route = empty_route()
        route[4]["market"] = "not-a-list"
        staged, report = compile_jit_expensive_seed_routes({"R": route})
        self.assertEqual(staged["R"], route)
        self.assertEqual(report["reason"], "malformed_route")

    def test_36_route_length_mismatch(self):
        left, right = empty_route(24), empty_route(23)
        staged, report = compile_jit_expensive_seed_routes({"LEFT": left, "RIGHT": right})
        self.assertEqual(staged, {"LEFT": left, "RIGHT": right})
        self.assertEqual(report["reason"], "route_length_mismatch")


if __name__ == "__main__":
    unittest.main()
