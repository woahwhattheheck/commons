# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

HERE = Path(__file__).resolve().parent

fake = types.ModuleType("r04_full_router")
fake._POLICY = None
def _native_day(native, day):
    return native.days[day]
fake._v219_native_day = _native_day
sys.modules["r04_full_router"] = fake

spec = importlib.util.spec_from_file_location("p02", HERE / "goose_capacity_economy.py")
p02 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p02)


class Native:
    def __init__(self, days):
        self.days = days


def day(hands=2, hire_hour=0, market_extra=0):
    cards = []
    for hour in range(24):
        market = [["SELL", "CARROT", 1] for _ in range(market_extra)]
        if hour == hire_hour:
            market = market + [["HIRE"] for _ in range(hands)]
        cards.append({"farmer": ["PASS"], "hands": [["PASS"] for _ in range(hands)], "market": market})
    return cards


class P02Contracts(unittest.TestCase):
    def setUp(self):
        p02.reset()

    def test_projected_eggs_care_bound(self):
        self.assertEqual(p02._eggs(12), 32)
        self.assertEqual(p02._eggs(18), 20)

    def test_schedule_rejects_late_route_hire(self):
        native = Native({d: day(hands=2, hire_hour=(22 if d == 13 else 0)) for d in range(12, 30)})
        self.assertIsNone(p02._schedule(native, 12, (7, 4), 0))

    def test_schedule_places_our_hires_after_parent_workforce(self):
        native = Native({d: day(hands=3, hire_hour=1) for d in range(12, 30)})
        schedule, hire_cost, _distance = p02._schedule(native, 12, (7, 4), 0)
        self.assertEqual(schedule[12], {"hour": 4, "expected": 3})
        self.assertGreater(hire_cost, 0)

    def test_schedule_rejects_market_slot_exhaustion(self):
        native = Native({d: day(hands=2, hire_hour=0, market_extra=(7 if d == 12 else 0)) for d in range(12, 30)})
        self.assertIsNone(p02._schedule(native, 12, (5, 4), 0))

    def test_walk_is_deterministic(self):
        self.assertEqual(p02._walk([4, 4], (6, 5)), ["EAST"])
        self.assertEqual(p02._walk([6, 4], (6, 5)), ["SOUTH"])
        self.assertEqual(p02._walk([6, 5], (6, 5)), ["PASS"])

    def test_empty_coop_and_goose_count(self):
        tiles = [[None for _ in range(10)] for _ in range(10)]
        tiles[1][2] = {"kind": "COOP"}
        tiles[2][2] = {"kind": "COOP", "animal": "GOOSE"}
        farm = {"tiles": tiles}
        private = {"shed": {"GOOSE": 1}, "inventories": [{"GOOSE": 2}]}
        self.assertEqual(p02._empty_coops(farm), [(2, 1)])
        self.assertEqual(p02._geese(farm, private), 4)

    def test_disabled_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        self.assertIs(p02.apply_goose_capacity_economy(action, {}, {}, enabled=False), action)

    def test_nonstandard_config_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        cfg = dict(p02.CFG)
        cfg["shedCapacity"] = 99
        obs = {"step": 200, "player": 0, "farms": [{}, {}], "private": {}}
        self.assertIs(p02.apply_goose_capacity_economy(action, obs, cfg, enabled=True), action)

    def test_same_step_does_not_append_twice(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        cfg = dict(p02.CFG)
        obs = {"step": 200, "player": 0, "farms": [{}, {}], "private": {}}
        state = p02._state(0, 200)
        state["last"] = 200
        self.assertIs(p02.apply_goose_capacity_economy(action, obs, cfg, enabled=True), action)


if __name__ == "__main__":
    unittest.main()
