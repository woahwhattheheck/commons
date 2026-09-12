# SPDX-License-Identifier: Apache-2.0
"""Pinned-engine raw market-prefix parity for the standalone SELL scheduler."""
from __future__ import annotations

import copy
import unittest

import scheduler


class _Controller:
    def __init__(self, base, route):
        self.base = copy.deepcopy(base)
        self.cur = "r"
        self.R = {"r": route}

    def act(self, _obs):
        return copy.deepcopy(self.base)


class SchedulerMarketPrefixTests(unittest.TestCase):
    @staticmethod
    def _route(length=64):
        return [
            {"farmer": ["PASS"], "hands": [], "market": []}
            for _ in range(length)
        ]

    @staticmethod
    def _obs(step=5):
        return {
            "step": step,
            "player": 0,
            "farms": [
                {"tiles": [], "unlocked_quadrants": [0], "hires_today": 0},
                {"tiles": []},
            ],
            "market": {"inventory": {"MILK": 100}, "params": None, "prices": {}},
            "town": {"unlocked_shops": []},
            "private": {},
        }

    def test_market_limit_matches_pinned_engine_nonpositive_floor(self):
        self.assertEqual(scheduler._market_order_limit({}), 10)
        self.assertEqual(scheduler._market_order_limit({"maxMarketOrdersPerTurn": 0}), 1)
        self.assertEqual(scheduler._market_order_limit({"maxMarketOrdersPerTurn": -9}), 1)
        self.assertEqual(scheduler._market_order_limit({"maxMarketOrdersPerTurn": 2.9}), 2)

    def test_cash_reserve_ignores_cap_truncated_hire(self):
        base = {"market": [[], ["HIRE"]]}
        s = scheduler.SellScheduler("naive")
        s.controller = _Controller(base, self._route())
        cost = s.cash_reserve(
            self._obs(),
            {"maxMarketOrdersPerTurn": 1},
            base,
            5,
        )
        self.assertEqual(cost, 0)

    def test_receipt_profile_ignores_suffix_sell_capacity_credit(self):
        base = {"market": [[], ["SELL", "EGGS", 1]]}
        s = scheduler.SellScheduler()
        s.controller = _Controller(base, self._route())
        original = scheduler.post_units
        scheduler.post_units = lambda *_a, **_k: (
            {"tiles": [], "hands": []},
            {"shed": {"MILK": 4, "EGGS": 1}, "inventories": []},
        )
        try:
            feasible = s.receipt_profile(
                {"step": 5}, base, {}, {}, 5, "MILK",
                {"shedCapacity": 5, "maxMarketOrdersPerTurn": 1},
            )
            self.assertFalse(feasible(()))
        finally:
            scheduler.post_units = original

    def test_receipt_profile_ignores_suffix_buy_overflow(self):
        base = {"market": [[], ["BUY_PRODUCT", "MILK", 2]]}
        s = scheduler.SellScheduler()
        s.controller = _Controller(base, self._route())
        original = scheduler.post_units
        scheduler.post_units = lambda *_a, **_k: (
            {"tiles": [], "hands": []},
            {"shed": {"MILK": 3}, "inventories": []},
        )
        try:
            feasible = s.receipt_profile(
                {"step": 5}, base, {}, {}, 5, "MILK",
                {"shedCapacity": 5, "maxMarketOrdersPerTurn": 1},
            )
            self.assertTrue(feasible(()))
        finally:
            scheduler.post_units = original

    def test_receipt_profile_never_spawns_suffix_hire(self):
        base = {"market": [[], ["HIRE"]]}
        s = scheduler.SellScheduler()
        s.controller = _Controller(base, self._route())
        original_post = scheduler.post_units
        original_spawn = scheduler.m._spawn_hand
        scheduler.post_units = lambda *_a, **_k: (
            {"tiles": [], "hands": []},
            {"shed": {"MILK": 0}, "inventories": []},
        )

        def forbidden(*_a, **_k):
            raise AssertionError("cap-truncated HIRE must be projection-inert")

        scheduler.m._spawn_hand = forbidden
        try:
            feasible = s.receipt_profile(
                {"step": 5}, base, {}, {}, 5, "MILK",
                {"shedCapacity": 5, "maxMarketOrdersPerTurn": 1},
            )
            self.assertTrue(feasible(()))
        finally:
            scheduler.post_units = original_post
            scheduler.m._spawn_hand = original_spawn

    def test_act_preserves_suffix_bytes_and_pending_uses_executable_sells_only(self):
        base = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "MILK", 1], ["SELL", "MILK", 99]],
        }
        s = scheduler.SellScheduler("naive")
        s.controller = _Controller(base, self._route())
        original = scheduler.post_units
        scheduler.post_units = lambda *_a, **_k: (
            {"money": 100, "tiles": [], "hands": []},
            {"shed": {"MILK": 5}, "inventories": []},
        )
        try:
            out = s.act(
                self._obs(),
                {"maxMarketOrdersPerTurn": 1, "episodeSteps": 720},
            )
        finally:
            scheduler.post_units = original
        self.assertEqual(out["market"], base["market"])
        self.assertEqual(s.pending.get("MILK"), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
