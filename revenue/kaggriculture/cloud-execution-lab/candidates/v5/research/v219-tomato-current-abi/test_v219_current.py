# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v219_current", HERE / "v219_current.py")
v219 = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise RuntimeError("unable to load v219_current")
spec.loader.exec_module(v219)

CFG = {
    "boardSize": 10,
    "turnsPerDay": 24,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
    "farmHandCostMult": 1,
}


def route(hands=0):
    action = {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(hands)], "market": []}
    return [copy.deepcopy(action) for _ in range(v219.LAST_STEP + 1)]


def route_sha(value):
    return v219._canonical_route(value)[1]


def observation(step=v219.QUALIFY_STEP, *, hands=0, money=12000, tomato_price=80,
                unlocked=None, tomato_seed=0, tomato_shed=0, fertilizer=20):
    unlocked = ["NW", "NE", "SW"] if unlocked is None else list(unlocked)
    tiles = [["LOCKED" for _ in range(10)] for _ in range(10)]
    for y in range(5):
        for x in range(10):
            tiles[y][x] = None
    for y in range(5, 10):
        for x in range(5):
            tiles[y][x] = None
    farm = {
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [[4, 4] for _ in range(hands)],
        "money": money,
        "unlocked_quadrants": unlocked,
        "hires_today": 0,
    }
    private = {
        "inventories": [{} for _ in range(hands + 1)],
        "shed": {"WHEAT": 20, "TOMATO": tomato_shed, "FERTILIZER": 20},
        "seeds": {"TOMATO": tomato_seed},
    }
    prices = {item: 10 for item in v219.PRODUCTS}
    prices["TOMATO"] = tomato_price
    prices["FERTILIZER"] = fertilizer
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [farm, copy.deepcopy(farm)],
        "private": private,
        "market": {"prices": prices},
        "town": {"unlocked_shops": ["PIZZA_SHOP", "FARMERS_MARKET", "PIZZA_SHOP"]},
    }


def selected(hands=0, market=None):
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in range(hands)],
        "market": [] if market is None else copy.deepcopy(market),
    }


class V219CurrentTests(unittest.TestCase):
    def test_disabled_is_exact_identity_and_no_state_mutation(self):
        r = route()
        s = v219.new_state()
        action = selected()
        before_state = copy.deepcopy(s)
        before_action = copy.deepcopy(action)
        out, later, report = v219.apply(
            observation(), action, CFG, enabled=False,
            route_snapshot=r, route_sha256=route_sha(r), state=s)
        self.assertEqual(out, before_action)
        self.assertEqual(later, before_state)
        self.assertEqual(action, before_action)
        self.assertEqual(s, before_state)
        self.assertEqual(report["reason"], "disabled")

    def test_route_digest_mismatch_fails_closed(self):
        r = route()
        out, later, report = v219.apply(
            observation(), selected(), CFG, enabled=True,
            route_snapshot=r, route_sha256="0" * 64, state=v219.new_state())
        self.assertEqual(out, selected())
        self.assertEqual(later["qualified"], False)
        self.assertEqual(report["reason"], "route-authority")

    def test_step433_qualifies_and_requests_initial_investment(self):
        r = route()
        out, state, report = v219.apply(
            observation(), selected(), CFG, enabled=True,
            route_snapshot=r, route_sha256=route_sha(r), state=v219.new_state())
        self.assertTrue(state["qualified"])
        self.assertTrue(state["eligible"])
        self.assertTrue(state["committed"])
        self.assertEqual(state["route_sha256"], route_sha(r))
        self.assertEqual(out["market"], [
            ["BUY_LAND"], ["BUY_SEED", "TOMATO", 10], ["HIRE"], ["HIRE"]
        ])
        self.assertTrue(report["applied"])
        self.assertEqual(report["hire_requests"], 2)

    def test_qualification_rejects_current_route_land_or_tomato_ownership(self):
        for conflict in (["BUY_LAND"], ["PLANT", "TOMATO"]):
            with self.subTest(conflict=conflict):
                r = route()
                if conflict[0] == "BUY_LAND":
                    r[500]["market"] = [conflict]
                else:
                    r[500]["farmer"] = conflict
                out, state, report = v219.apply(
                    observation(), selected(), CFG, enabled=True,
                    route_snapshot=r, route_sha256=route_sha(r), state=v219.new_state())
                self.assertFalse(state["eligible"])
                self.assertFalse(state["committed"])
                self.assertEqual(out, selected())
                self.assertEqual(report["reason"], "not-eligible")

    def test_qualification_rejects_donor_public_preconditions(self):
        cases = [
            observation(money=11999),
            observation(tomato_price=69),
            observation(tomato_seed=1),
            observation(tomato_shed=1),
        ]
        r = route()
        for obs in cases:
            with self.subTest(obs=obs["private"]):
                out, state, _ = v219.apply(
                    obs, selected(), CFG, enabled=True,
                    route_snapshot=r, route_sha256=route_sha(r), state=v219.new_state())
                self.assertFalse(state["eligible"])
                self.assertEqual(out, selected())

    def test_future_native_hire_blocks_same_day_request(self):
        r = route()
        r[440]["market"] = [["HIRE"]]
        out, state, report = v219.apply(
            observation(), selected(), CFG, enabled=True,
            route_snapshot=r, route_sha256=route_sha(r), state=v219.new_state())
        self.assertTrue(state["eligible"])
        self.assertFalse(state["committed"])
        self.assertEqual(out, selected())
        self.assertEqual(report["request_block"], "future-native-hire")

    def test_budget_guard_preserves_parent(self):
        r = route()
        obs = observation(money=7000)
        state = v219.new_state()
        state.update(qualified=True, eligible=True, route_sha256=route_sha(r), last_step=432)
        out, later, report = v219.apply(
            obs, selected(), CFG, enabled=True,
            route_snapshot=r, route_sha256=route_sha(r), state=state)
        self.assertEqual(out, selected())
        self.assertFalse(later["committed"])
        self.assertGreater(report["budget_decline"], 0)

    def test_pending_hires_confirm_workers_then_start_se_work(self):
        r = route()
        digest = route_sha(r)
        _first, state, _ = v219.apply(
            observation(), selected(), CFG, enabled=True,
            route_snapshot=r, route_sha256=digest, state=v219.new_state())
        obs = observation(434, hands=2, unlocked=["NW", "NE", "SW", "SE"])
        obs["private"]["seeds"]["TOMATO"] = 10
        for y in (5, 6):
            for x in range(5, 10):
                obs["farms"][0]["tiles"][y][x] = None
        out, later, report = v219.apply(
            obs, selected(hands=2), CFG, enabled=True,
            route_snapshot=r, route_sha256=digest, state=state)
        self.assertEqual(report["confirmed_workers"], 2)
        self.assertEqual(sorted(int(k) for k in later["workers"]), [1, 2])
        self.assertIn(out["hands"][0][0], {"EAST", "SOUTH", "PLANT"})
        self.assertIn(out["hands"][1][0], {"EAST", "SOUTH", "PLANT"})

    def test_route_drift_after_qualification_aborts_new_work(self):
        r = route()
        digest = route_sha(r)
        _out, state, _ = v219.apply(
            observation(), selected(), CFG, enabled=True,
            route_snapshot=r, route_sha256=digest, state=v219.new_state())
        changed = route()
        changed[500]["market"] = [["SELL", "WHEAT", 1]]
        changed_digest = route_sha(changed)
        obs = observation(434, hands=0)
        out, later, report = v219.apply(
            obs, selected(), CFG, enabled=True,
            route_snapshot=changed, route_sha256=changed_digest, state=state)
        self.assertEqual(out, selected())
        self.assertFalse(later["eligible"])
        self.assertEqual(report["reason"], "route-drift")

    def test_physical_tomato_stock_gets_one_sell_row(self):
        r = route()
        digest = route_sha(r)
        state = v219.new_state()
        state.update(qualified=True, eligible=True, committed=True,
                     route_sha256=digest, requested_day=18, day=18, last_step=433)
        obs = observation(434, tomato_shed=7)
        out, later, report = v219.apply(
            obs, selected(), CFG, enabled=True,
            route_snapshot=r, route_sha256=digest, state=state)
        self.assertEqual(out["market"], [["SELL", "TOMATO", 7]])
        self.assertEqual(report["tomato_sale_requests"], 7)
        self.assertTrue(later["committed"])

    def test_existing_tomato_sell_is_not_duplicated(self):
        r = route()
        digest = route_sha(r)
        state = v219.new_state()
        state.update(qualified=True, eligible=True, committed=True,
                     route_sha256=digest, requested_day=18, day=18, last_step=433)
        parent = selected(market=[["SELL", "TOMATO", 3]])
        out, _later, report = v219.apply(
            observation(434, tomato_shed=7), parent, CFG, enabled=True,
            route_snapshot=r, route_sha256=digest, state=state)
        self.assertEqual(out["market"], parent["market"])
        self.assertNotIn("tomato_sale_requests", report)

    def test_terminal_return_prioritizes_carried_tomato(self):
        r = route(hands=1)
        digest = route_sha(r)
        state = v219.new_state()
        state.update(qualified=True, eligible=True, committed=True,
                     route_sha256=digest, requested_day=29, day=29, last_step=717,
                     workers={1: {"kind": "crop", "targets": [(5, 5)], "needs_fertilizer": False}})
        obs = observation(718, hands=1, unlocked=["NW", "NE", "SW", "SE"])
        obs["farms"][0]["hands"][0] = [5, 5]
        obs["private"]["inventories"][1] = {"TOMATO": 4}
        obs["farms"][0]["tiles"][5][5] = {"kind": "SOIL", "crop": "TOMATO", "watered_today": True, "yield_units": 0}
        out, _later, _report = v219.apply(
            obs, selected(hands=1), CFG, enabled=True,
            route_snapshot=r, route_sha256=digest, state=state)
        self.assertEqual(out["hands"][0], ["PLACE", "TOMATO", 4])

    def test_malformed_or_nonstandard_config_fails_closed(self):
        r = route()
        for bad in (
            {**CFG, "shedCapacity": 99},
            {**CFG, "farmHandCostMult": True},
            {**CFG, "turnsPerDay": 25},
        ):
            with self.subTest(bad=bad):
                out, _state, report = v219.apply(
                    observation(), selected(), bad, enabled=True,
                    route_snapshot=r, route_sha256=route_sha(r), state=v219.new_state())
                self.assertEqual(out, selected())
                self.assertEqual(report["reason"], "unsupported-config")


if __name__ == "__main__":
    unittest.main()
