# SPDX-License-Identifier: Apache-2.0
"""Focused contracts for the append-only TITAN V3 market-carry candidate."""
from __future__ import annotations

from copy import deepcopy
import math
import random
import unittest

from market_carry import MarketCarry


class Mechanics:
    PRODUCTS = (
        "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
        "EGG", "MILK", "WOOL", "FERTILIZER",
    )
    ANIMALS = {
        "GOOSE": {"product": "EGG"},
        "COW": {"product": "MILK"},
        "SHEEP": {"product": "WOOL"},
    }
    SHOPS = {
        "BAKERY": ("EGG", "WHEAT"),
        "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
        "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
        "YARN_STORE": ("WOOL",),
        "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
        "PET_CAFE": ("CARROT",),
        "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
        "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
    }
    PARAMS = {
        "WHEAT":      {"base": 25, "I0": 10000, "T": 400, "below_func": "sqrt", "below_target": .80, "above_func": "log", "above_target": .20},
        "CARROT":     {"base": 35, "I0": 10000, "T": 450, "below_func": "hinge", "below_target": 1.00, "above_func": "sqrt", "above_target": .70},
        "TOMATO":     {"base": 60, "I0": 10000, "T": 200, "below_func": "hinge", "below_target": .40, "above_func": "sqrt", "above_target": .60},
        "STRAWBERRY": {"base": 120, "I0": 10000, "T": 100, "below_func": "sqrt", "below_target": .70, "above_func": "linear", "above_target": 1.60},
        "MELON":      {"base": 250, "I0": 10000, "T": 300, "below_func": "log", "below_target": .20, "above_func": "sq", "above_target": 3.60},
        "EGG":        {"base": 50, "I0": 10000, "T": 332, "below_func": "hinge", "below_target": .40, "above_func": "log", "above_target": .20},
        "MILK":       {"base": 160, "I0": 10000, "T": 122, "below_func": "sqrt", "below_target": .60, "above_func": "linear", "above_target": 1.60},
        "WOOL":       {"base": 200, "I0": 10000, "T": 105, "below_func": "log", "below_target": .20, "above_func": "sq", "above_target": 3.20},
        "FERTILIZER": {"base": 100, "I0": 10000, "T": 200, "below_func": "linear", "below_target": .40, "above_func": "linear", "above_target": .40},
    }

    @staticmethod
    def _shape(name, x, threshold):
        x = max(0.0, x)
        if name == "linear":
            return x
        if name == "sq":
            return x * x
        if name == "sqrt":
            return math.sqrt(x)
        if name == "log":
            return math.log(1.0 + x)
        if name == "hinge":
            u = x / threshold
            return u + 8.0 * max(0.0, u - 1.0) ** 2
        raise AssertionError(name)

    @classmethod
    def market_price(cls, item, inventory, params=None):
        p = (params or cls.PARAMS)[item]
        base, i0, threshold = p["base"], p["I0"], p["T"]
        if inventory < i0:
            name, target = p["below_func"], p["below_target"]
            amplitude = target * base / cls._shape(name, threshold, threshold)
            raw = base + amplitude * cls._shape(name, i0 - inventory, threshold)
        else:
            name, target = p["above_func"], p["above_target"]
            amplitude = target * base / cls._shape(name, threshold, threshold)
            raw = base - amplitude * cls._shape(name, inventory - i0, threshold)
        return max(1, int(round(raw)))


CFG = {
    "episodeSteps": 720,
    "turnsPerDay": 24,
    "maxMarketOrdersPerTurn": 10,
    "shedCapacity": 100,
    "townShopSellInterval": 4,
    "townCenterSellInterval": 24,
}


def blank_tiles():
    return [[None for _ in range(10)] for _ in range(10)]


def observation(
    step=120,
    *,
    cash=10_000,
    shops=("SMOOTHIE_SHOP",) * 4,
    shed=None,
    inventory=None,
    rival_tiles=None,
):
    own = {
        "money": cash,
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
        "farmer": [4, 4],
        "hands": [],
        "tiles": blank_tiles(),
    }
    rival = {
        "money": 3_000,
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
        "farmer": [5, 5],
        "hands": [],
        "tiles": rival_tiles if rival_tiles is not None else blank_tiles(),
    }
    market_inventory = {item: 10_000 for item in Mechanics.PRODUCTS}
    market_inventory.update(inventory or {})
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [own, rival],
        "private": {
            "shed": dict(shed or {}),
            "inventories": [{}],
            "seeds": {},
        },
        "market": {"inventory": market_inventory, "params": None},
        "town": {"unlocked_shops": list(shops)},
    }


def action(market=None, farmer=None, hands=None):
    return {
        "farmer": list(farmer or ["PASS"]),
        "hands": deepcopy(hands or []),
        "market": deepcopy(market or []),
    }


def projected(obs, selected, _cfg):
    # The focused tests use no unit-stage shed mutation unless they replace
    # this callback explicitly.
    return deepcopy(obs["farms"][obs["player"]]), deepcopy(obs["private"])


class MarketCarryContracts(unittest.TestCase):
    def overlay(self, **kwargs):
        return MarketCarry(Mechanics, post_units=projected, **kwargs)

    def test_profitable_tick_appends_one_trailing_buy_and_preserves_parent(self):
        base = action(
            [["SELL", "WHEAT", 2]],
            farmer=["WATER"],
            hands=[["CARE"]],
        )
        before = deepcopy(base)
        out, report = self.overlay().transform(observation(), CFG, base)
        self.assertTrue(report["changed"])
        self.assertEqual(report["reason"], "append_carry_buy")
        self.assertEqual(out["market"][:-1], before["market"])
        self.assertEqual(out["farmer"], before["farmer"])
        self.assertEqual(out["hands"], before["hands"])
        self.assertEqual(out["market"][-1], ["BUY_PRODUCT", "STRAWBERRY", 12])
        self.assertEqual(report["append_index"], 1)
        self.assertGreaterEqual(report["entry"]["worst_profit"], 12)
        self.assertEqual(base, before, "parent action must not be mutated")

    def test_no_visible_absorption_is_a_noop(self):
        base = action()
        out, report = self.overlay().transform(
            observation(step=121, shops=()), CFG, base
        )
        self.assertIs(out, base)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "no_positive_carry")

    def test_existing_spend_or_full_queue_fails_closed(self):
        for market in (
            [["BUY_SEED", "WHEAT", 1]],
            [["HIRE"]],
            [["BUY_LAND"]],
            [["BUY_ANIMAL", "COW", 1]],
            [["BUY_PRODUCT", "MILK", 1]],
            [["SELL", "WHEAT", 1]] * 10,
        ):
            with self.subTest(market=market):
                base = action(market)
                out, report = self.overlay().transform(observation(), CFG, base)
                self.assertIs(out, base)
                self.assertEqual(report["reason"], "inherited_market_not_append_safe")

    def test_exact_post_unit_capacity_blocks_purchase(self):
        def full_after_units(obs, selected, cfg):
            private = deepcopy(obs["private"])
            private["shed"] = {"WHEAT": cfg["shedCapacity"]}
            return deepcopy(obs["farms"][0]), private

        base = action(farmer=["DROP"])
        out, report = MarketCarry(
            Mechanics, post_units=full_after_units
        ).transform(observation(), CFG, base)
        self.assertIs(out, base)
        self.assertEqual(report["reason"], "no_post_unit_capacity")

    def test_cash_reserve_is_never_funded_by_same_turn_sales(self):
        base = action([["SELL", "MELON", 99]])
        out, report = self.overlay().transform(
            observation(cash=1_000, shed={"MELON": 99}), CFG, base
        )
        self.assertIs(out, base)
        self.assertEqual(report["reason"], "cash_reserve")

    def test_same_product_parent_sale_excludes_only_that_product(self):
        base = action([["SELL", "STRAWBERRY", 2]])
        out, report = self.overlay().transform(observation(), CFG, base)
        self.assertTrue(report["changed"])
        self.assertNotEqual(out["market"][-1][1], "STRAWBERRY")
        self.assertEqual(out["market"][:-1], base["market"])

    def test_public_rival_yield_can_veto_a_trade(self):
        tiles = blank_tiles()
        tiles[0][0] = {
            "kind": "PASTURE",
            "animal": "COW",
            "yield_units": 12,
        }
        tiles[0][1] = {
            "kind": "PLANT",
            "crop": "STRAWBERRY",
            "yield_units": 12,
        }
        base = action()
        out, report = self.overlay().transform(
            observation(
                shops=("SMOOTHIE_SHOP",),
                rival_tiles=tiles,
            ),
            CFG,
            base,
        )
        self.assertIs(out, base)
        self.assertFalse(report["changed"])
        self.assertTrue(
            any(
                row.get("reason") == "demand_not_above_supply_stress"
                for row in report["evaluated"]
            )
        )

    def test_active_lot_prevents_stacking_until_seller_liquidates(self):
        overlay = self.overlay()
        base = action()
        first, report = overlay.transform(observation(step=120), CFG, base)
        item = first["market"][-1][1]
        quantity = first["market"][-1][2]
        held_obs = observation(step=121, shed={item: quantity})
        held, held_report = overlay.transform(held_obs, CFG, base)
        self.assertIs(held, base)
        self.assertEqual(held_report["reason"], "active_carry")
        sold_obs = observation(step=122, shed={item: 0})
        sold, sold_report = overlay.transform(sold_obs, CFG, base)
        self.assertIs(sold, base)
        self.assertEqual(sold_report["reason"], "no_positive_carry")
        self.assertEqual(
            sold_report["prior"]["reason"], "seller_liquidated_carry"
        )
        self.assertIsNone(overlay.active)

    def test_unfilled_order_clears_without_stacking_off_tick(self):
        overlay = self.overlay()
        base = action()
        first, _ = overlay.transform(observation(step=120), CFG, base)
        self.assertEqual(first["market"][-1][0], "BUY_PRODUCT")
        second, report = overlay.transform(observation(step=121), CFG, base)
        self.assertIs(second, base)
        self.assertEqual(report["prior"]["reason"], "prior_buy_not_observed")
        self.assertIsNone(overlay.active)

    def test_opening_and_terminal_buffers_are_protected(self):
        base = action()
        for step, expected in ((72, "opening_protected"), (671, "terminal_buffer")):
            with self.subTest(step=step):
                out, report = self.overlay().transform(
                    observation(step=step), CFG, base
                )
                self.assertIs(out, base)
                self.assertEqual(report["reason"], expected)

    def test_fuzz_invariant_is_prefix_preserving_and_bounded(self):
        rng = random.Random(260909)
        for case in range(300):
            step = rng.randrange(96, 670)
            step -= step % 4
            cash = rng.randrange(0, 50_001)
            market = []
            for _ in range(rng.randrange(0, 10)):
                if rng.randrange(4) == 0:
                    market.append([])
                else:
                    market.append(
                        [
                            "SELL",
                            rng.choice(Mechanics.PRODUCTS[:-1]),
                            rng.randrange(0, 20),
                        ]
                    )
            base = action(
                market,
                farmer=[rng.choice(("PASS", "NORTH", "WATER", "DROP"))],
                hands=[["PASS"]] * rng.randrange(0, 4),
            )
            before = deepcopy(base)
            overlay = self.overlay()
            out, report = overlay.transform(
                observation(step=step, cash=cash), CFG, base
            )
            self.assertEqual(base, before)
            self.assertEqual(out["farmer"], before["farmer"])
            self.assertEqual(out["hands"], before["hands"])
            self.assertLessEqual(len(out["market"]), CFG["maxMarketOrdersPerTurn"])
            self.assertEqual(out["market"][: len(before["market"])], before["market"])
            self.assertIn(len(out["market"]) - len(before["market"]), (0, 1))
            if report["changed"]:
                appended = out["market"][-1]
                self.assertEqual(appended[0], "BUY_PRODUCT")
                self.assertIn(appended[1], Mechanics.PRODUCTS[:-1])
                self.assertGreater(appended[2], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
