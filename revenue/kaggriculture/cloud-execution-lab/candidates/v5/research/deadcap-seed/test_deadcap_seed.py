# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import unittest

import deadcap_seed as d


def frame(*, farmer=None, hands=None, market=None):
    return {
        "farmer": ["PASS"] if farmer is None else farmer,
        "hands": [] if hands is None else hands,
        "market": [] if market is None else market,
    }


class DeadcapSeedTests(unittest.TestCase):
    def test_parser_matches_pinned_buy_seed_representation(self):
        self.assertEqual(d.parse_seed_buy(["BUY_SEED", "MELON", "2", "opaque"]), ("MELON", 2))
        self.assertEqual(d.parse_seed_buy(["BUY_SEED", "MELON", 2.9]), ("MELON", 2))
        self.assertEqual(d.parse_seed_buy(["BUY_SEED", "MELON", True]), ("MELON", 1))
        for row in (("BUY_SEED", "MELON", 1), ["BUY_SEED"], ["BUY_SEED", "MELON", "x"],
                    ["BUY_SEED", "PUMPKIN", 1], ["BUY_SEED", "MELON", 0], []):
            self.assertIsNone(d.parse_seed_buy(row))

    def test_all_routes_must_lack_future_plant(self):
        routes = {
            "a": [frame(), frame(market=[["BUY_SEED", "MELON", 1]]), frame()],
            "b": [frame(), frame(), frame(farmer=["PLANT", "MELON"])],
        }
        self.assertFalse(d.no_future_plant_in_route_family(routes, "MELON", 1))
        routes["b"][2] = frame()
        self.assertTrue(d.no_future_plant_in_route_family(routes, "MELON", 1))
        routes["b"][2] = {"farmer": ["PASS"], "hands": None, "market": []}
        self.assertIsNone(d.no_future_plant_in_route_family(routes, "MELON", 1))

    def test_same_callback_plant_does_not_rescue_later_market_buy(self):
        routes = {"a": [frame(farmer=["PLANT", "MELON"], market=[["BUY_SEED", "MELON", 1]]), frame()]}
        self.assertTrue(d.no_future_plant_in_route_family(routes, "MELON", 0))

    def test_transform_replaces_only_exact_executable_slot(self):
        routes = {"a": [frame(), frame(), frame()]}
        original = {
            "farmer": ["NORTH"], "hands": [["PASS"]],
            "market": [["SELL", "EGG", 1], ["BUY_SEED", "MELON", "2", "tag"], ["HIRE"]],
        }
        out, report = d.transform_with_report(
            original, step=1, routes=routes, enabled=True, route_family_complete=True,
            dynamic_unit_rewriters=False,
        )
        self.assertEqual(out["market"], [["SELL", "EGG", 1], [], ["HIRE"]])
        self.assertEqual(out["farmer"], original["farmer"])
        self.assertEqual(out["hands"], original["hands"])
        self.assertEqual(report["removed"], [{"index": 1, "crop": "MELON", "quantity": 2}])
        self.assertEqual(original["market"][1], ["BUY_SEED", "MELON", "2", "tag"])

    def test_cap_zero_and_negative_match_engine_floor_one(self):
        routes = {"a": [frame(), frame()]}
        action = {"farmer": ["PASS"], "hands": [], "market": [
            ["BUY_SEED", "MELON", 1], ["BUY_SEED", "CARROT", 1],
        ]}
        for cap in (0, -3):
            out = d.transform(
                action, step=0, routes=routes, configuration={"maxMarketOrdersPerTurn": cap},
                enabled=True, route_family_complete=True, dynamic_unit_rewriters=False,
            )
            self.assertEqual(out["market"], [[], ["BUY_SEED", "CARROT", 1]])

    def test_suffix_invalid_and_live_rows_are_unchanged(self):
        routes = {"a": [frame(), frame(farmer=["PLANT", "CARROT"])]}
        action = {"farmer": ["PASS"], "hands": [], "market": [
            ["BUY_SEED", "CARROT", 1],
            ["BUY_SEED", "MELON", 1],
            ["BUY_SEED", "MELON", "x"],
        ]}
        out = d.transform(
            action, step=0, routes=routes, configuration={"maxMarketOrdersPerTurn": 1},
            enabled=True, route_family_complete=True, dynamic_unit_rewriters=False,
        )
        self.assertEqual(out, action)

    def test_fail_closed_activation_and_route_uncertainty(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "MELON", 1]]}
        routes = {"a": [frame(), frame()]}
        for kwargs in (
            {},
            {"enabled": 1, "route_family_complete": True},
            {"enabled": True, "route_family_complete": False},
            {"enabled": True, "route_family_complete": True, "dynamic_unit_rewriters": True},
        ):
            self.assertEqual(d.transform(action, step=0, routes=routes, **kwargs), action)
        malformed = {"a": [frame(), {"farmer": ["PASS"], "hands": None, "market": []}]}
        out, report = d.transform_with_report(
            action, step=0, routes=malformed, enabled=True, route_family_complete=True,
            dynamic_unit_rewriters=False,
        )
        self.assertEqual(out, action)
        self.assertEqual(report["reason"], "route_proof_failed")

    def test_static_census_is_all_route_conservative_and_prefix_bounded(self):
        routes = {
            "a": [frame(market=[["BUY_SEED", "MELON", 1], ["BUY_SEED", "CARROT", 1]]), frame()],
            "b": [frame(), frame(farmer=["PLANT", "CARROT"])],
        }
        report = d.census_authored_routes(routes, {"maxMarketOrdersPerTurn": 1})
        self.assertTrue(report["certified"])
        self.assertEqual(report["rows"], [{
            "route": "a", "step": 0, "index": 0, "crop": "MELON", "quantity": 1,
        }])


if __name__ == "__main__":
    unittest.main()
