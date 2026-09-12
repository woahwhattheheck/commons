# SPDX-License-Identifier: Apache-2.0
"""Focused contracts for the bulk-feeder frozen-route census."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("_bulk_feeder_census", HERE / "route_census.py")
census = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(census)


def rows(n=24):
    return [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(n)]


def put(route, turn, action):
    route[turn]["farmer"] = list(action)


class RouteCensusContracts(unittest.TestCase):
    def test_detects_same_day_refill_and_measures_backtrack_slack(self):
        route = rows()
        put(route, 0, ["PICKUP", "WHEAT", 1])
        put(route, 1, ["EAST"])
        put(route, 2, ["FEED"])
        # A -> shed -> B contains four avoidable backtracking moves.  With the
        # second unit already in-pocket, the refill callback is avoidable too.
        put(route, 3, ["WEST"])
        put(route, 4, ["WEST"])
        put(route, 5, ["PICKUP", "WHEAT", 1])
        put(route, 6, ["EAST"])
        put(route, 7, ["EAST"])
        put(route, 8, ["EAST"])
        put(route, 9, ["FEED"])

        found = census.find_opportunities(route, route_name="synthetic")
        self.assertEqual(len(found), 1)
        row = found[0]
        self.assertEqual(row["product"], "WHEAT")
        self.assertEqual(row["preload_turn"], 0)
        self.assertEqual(row["refill_turn"], 5)
        self.assertEqual(row["service_before"], 2)
        self.assertEqual(row["service_after"], 9)
        self.assertEqual(row["raw_moves"], 5)
        self.assertEqual(row["direct_moves"], 1)
        self.assertEqual(row["backtrack_moves"], 4)
        self.assertEqual(row["net"], [1, 0])
        self.assertEqual(row["direct_path"], ["EAST"])
        self.assertEqual(row["saved_slots_upper"], 5)

    def test_fertilizer_uses_same_refill_theorem(self):
        route = rows()
        put(route, 3, ["PICKUP", "FERTILIZER", "1"])
        put(route, 4, ["FERTILIZE"])
        put(route, 5, ["PICKUP", "FERTILIZER", 1.9, "metadata"])
        put(route, 6, ["FERTILIZE"])
        found = census.find_opportunities(route)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["refill_quantity_to_preload"], 1)
        self.assertEqual(found[0]["saved_slots_upper"], 1)

    def test_cross_day_refill_is_not_a_pocket_witness(self):
        route = rows(48)
        put(route, 22, ["PICKUP", "WHEAT", 2])
        put(route, 23, ["FEED"])
        put(route, 24, ["PICKUP", "WHEAT", 1])
        put(route, 25, ["FEED"])
        self.assertEqual(census.find_opportunities(route), [])

    def test_intervening_productive_action_rejects_static_rewrite(self):
        route = rows()
        put(route, 0, ["PICKUP", "WHEAT", 1])
        put(route, 1, ["FEED"])
        put(route, 2, ["WEST"])
        put(route, 3, ["HARVEST"])
        put(route, 4, ["PICKUP", "WHEAT", 1])
        put(route, 5, ["EAST"])
        put(route, 6, ["FEED"])
        self.assertEqual(census.find_opportunities(route), [])

    def test_wrong_product_and_nonpositive_or_malformed_pickups_are_inert(self):
        base = rows()
        for bad in (
            ["PICKUP", "CARROT", 1],
            ["PICKUP", "WHEAT", 0],
            ["PICKUP", "WHEAT", -1],
            ["PICKUP", "WHEAT", "x"],
            ["PICKUP", "WHEAT"],
            ("PICKUP", "WHEAT", 1),
        ):
            with self.subTest(bad=bad):
                route = deepcopy(base)
                route[0]["farmer"] = bad
                put(route, 1, ["FEED"])
                put(route, 2, ["PICKUP", "WHEAT", 1])
                put(route, 3, ["FEED"])
                self.assertEqual(census.find_opportunities(route), [])

    def test_scanner_is_diagnostic_only_and_sorted_by_upper_slack(self):
        small = rows()
        put(small, 0, ["PICKUP", "WHEAT", 1])
        put(small, 1, ["FEED"])
        put(small, 2, ["PICKUP", "WHEAT", 1])
        put(small, 3, ["FEED"])

        large = rows()
        put(large, 0, ["PICKUP", "WHEAT", 1])
        put(large, 1, ["FEED"])
        put(large, 2, ["WEST"])
        put(large, 3, ["PICKUP", "WHEAT", 1])
        put(large, 4, ["EAST"])
        put(large, 5, ["FEED"])

        report = census.scan_routes({"small": small, "large": large})
        self.assertEqual(report["schema"], census.SCHEMA)
        self.assertFalse(report["runtime_change"])
        self.assertFalse(report["production_change"])
        self.assertEqual(report["verdict"], "WITNESS")
        self.assertEqual(report["opportunity_count"], 2)
        self.assertEqual(report["opportunities"][0]["route"], "large")
        self.assertGreaterEqual(
            report["opportunities"][0]["saved_slots_upper"],
            report["opportunities"][1]["saved_slots_upper"],
        )

    def test_turns_per_day_requires_positive_plain_int(self):
        route = rows()
        for value in (0, -1, True, 24.0, "24"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    census.find_opportunities(route, turns_per_day=value)


if __name__ == "__main__":
    unittest.main()
