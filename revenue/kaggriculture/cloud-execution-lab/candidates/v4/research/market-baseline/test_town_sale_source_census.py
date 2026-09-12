#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import town_sale_source_census as census  # noqa: E402


class FakeEngine:
    PRODUCTS = ("MILK", "WOOL", "WHEAT")
    TOWN_CENTER_PRODUCTS = ("MILK", "WOOL", "WHEAT")
    SHOPS = {}
    MAX_SHOP_INSTANCES = 8


class FakeTiming:
    @staticmethod
    def town_demand_units(engine, step, unlocked_shops, config=None, item="WHEAT"):
        del unlocked_shops, config
        return 1 if step % 24 == 0 and item in engine.TOWN_CENTER_PRODUCTS else 0


def act(market=None, farmer=None, hands=None):
    return {
        "farmer": ["PASS"] if farmer is None else farmer,
        "hands": [] if hands is None else hands,
        "market": [] if market is None else market,
    }


class TownSellSourceCensusTests(unittest.TestCase):
    def test_quiet_next_callback_is_source_safe(self):
        route = [act() for _ in range(30)]
        route[24] = act([["SELL", "MILK", 5]])
        row = census.census_route("synthetic", route, FakeEngine, FakeTiming, max_orders=10)
        self.assertEqual(len(row["guaranteed_windows"]), 1)
        self.assertEqual(len(row["source_safe_windows"]), 1)
        self.assertEqual(row["source_safe_windows"][0]["step"], 24)

    def test_non_drain_sell_is_not_a_candidate(self):
        route = [act() for _ in range(30)]
        route[23] = act([["SELL", "MILK", 5]])
        row = census.census_route("synthetic", route, FakeEngine, FakeTiming, max_orders=10)
        self.assertEqual(row["guaranteed_windows"], [])

    def test_suffix_sell_is_not_executable_candidate(self):
        route = [act() for _ in range(30)]
        route[24] = act([[] for _ in range(10)] + [["SELL", "MILK", 5]])
        row = census.census_route("synthetic", route, FakeEngine, FakeTiming, max_orders=10)
        self.assertEqual(row["guaranteed_windows"], [])

    def test_next_market_cash_dependency_blocks(self):
        route = [act() for _ in range(30)]
        route[24] = act([["SELL", "MILK", 5]])
        route[25] = act([["HIRE", 1]])
        row = census.census_route("synthetic", route, FakeEngine, FakeTiming, max_orders=10)
        self.assertEqual(row["source_safe_windows"], [])
        self.assertIn("next_market_cash_or_order_dependency", row["guaranteed_windows"][0]["blockers"])

    def test_next_same_item_sell_blocks(self):
        route = [act() for _ in range(30)]
        route[24] = act([["SELL", "WOOL", 5]])
        route[25] = act([["SELL", "WOOL", 1]])
        row = census.census_route("synthetic", route, FakeEngine, FakeTiming, max_orders=10)
        self.assertIn("next_market_same_item_sell", row["guaranteed_windows"][0]["blockers"])

    def test_next_full_market_blocks_append(self):
        route = [act() for _ in range(30)]
        route[24] = act([["SELL", "MILK", 5]])
        route[25] = act([["SELL", "WOOL", 1] for _ in range(10)])
        row = census.census_route("synthetic", route, FakeEngine, FakeTiming, max_orders=10)
        self.assertIn("next_market_no_append_slot", row["guaranteed_windows"][0]["blockers"])

    def test_next_drop_or_place_blocks_shed_custody(self):
        for op in (["DROP"], ["PLACE", "MILK", 1]):
            with self.subTest(op=op):
                route = [act() for _ in range(30)]
                route[24] = act([["SELL", "MILK", 5]])
                route[25] = act(farmer=op)
                row = census.census_route("synthetic", route, FakeEngine, FakeTiming, max_orders=10)
                self.assertIn("next_unit_can_write_shed", row["guaranteed_windows"][0]["blockers"])

    def test_terminal_horizon_blocks(self):
        route = [act() for _ in range(720)]
        # 720 is a drain tick but cannot be executable; use helper directly at 718
        self.assertEqual(
            census.structural_blockers(route, 718, "MILK", max_orders=10),
            ["terminal_horizon"],
        )

    def test_current_sources_are_exact_and_report_is_deterministic(self):
        first = census.census()
        second = census.census()
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "titan-v4-townsell-source-census/v1")
        self.assertEqual(first["source_identity"]["arlene"], census.EXPECTED_ARLENE_BLOB)
        self.assertEqual(first["source_identity"]["engine"], census.EXPECTED_ENGINE_BLOB)
        self.assertEqual(first["source_identity"]["townsell"], census.EXPECTED_TOWNSELL_BLOB)
        self.assertEqual(first["source_identity"]["town_timing"], census.EXPECTED_TOWN_TIMING_BLOB)
        self.assertEqual(first["current_authority"]["route_count"], 4)
        self.assertIn(
            first["status"],
            ("SOURCE_SAFE_SHAPE_REQUIRES_CURRENT_NATIVE", "COLD_SOURCE_NO_SAFE_SHAPE"),
        )
        # Canonical JSON must also be deterministic; this is the receipt payload
        # used by the workflow and the downstream execution handoff.
        a = json.dumps(first, sort_keys=True, separators=(",", ":"))
        b = json.dumps(second, sort_keys=True, separators=(",", ":"))
        self.assertEqual(a, b)

    def test_every_current_safe_window_satisfies_published_source_guards(self):
        report = census.census()
        for row in report["source_safe_windows"]:
            self.assertEqual(row["blockers"], [])
            self.assertLessEqual(row["row_index"], 9)
            self.assertLess(row["step"], census.FINAL_EXECUTABLE_STEP)
            self.assertGreater(row["guaranteed_town_center_drain"], 0)
            self.assertGreater(row["authored_quantity"], 0)


if __name__ == "__main__":
    unittest.main()
