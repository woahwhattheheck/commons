# SPDX-License-Identifier: Apache-2.0
"""Focused contracts for the opt-in V5 close-game margin objective."""
import unittest
from copy import deepcopy

from close_game_margin import transform


PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER"]


def farm(money=3000, tiles=None):
    return {
        "money": money,
        "tiles": deepcopy(tiles) if tiles is not None else [[None] * 10 for _ in range(10)],
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }


def observation(step=700, own_money=10000, rival_money=5000, shed=None,
                rival_tiles=None, player=0, prices=None):
    own = farm(own_money)
    rival = farm(rival_money, rival_tiles)
    stock = {item: 0 for item in PRODUCTS}
    stock.update(shed or {})
    public_prices = {item: 10 for item in PRODUCTS}
    public_prices.update(prices or {})
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": player,
        "farms": [own, rival] if player == 0 else [rival, own],
        "private": {"shed": stock, "seeds": {}, "inventories": [{}]},
        "market": {"prices": public_prices, "inventory": {item: 10000 for item in PRODUCTS}},
        "town": {"unlocked_shops": []},
    }


CFG = {"episodeSteps": 720, "maxMarketOrdersPerTurn": 10}


def action(rows):
    return {"farmer": ["PASS"], "hands": [], "market": deepcopy(rows)}


class CloseGameMarginContracts(unittest.TestCase):
    def test_conservative_ahead_paces_existing_sell_without_reordering(self):
        selected = action([["SELL", "EGG", 12], ["BUY_SEED", "CARROT", 1]])
        result, report = transform(
            observation(shed={"EGG": 12}), CFG, selected, mode="adaptive")
        self.assertTrue(report["changed"])
        self.assertEqual(report["mode"], "conservative_ahead")
        self.assertEqual(result["market"], [["SELL", "EGG", 3], ["BUY_SEED", "CARROT", 1]])
        self.assertEqual(selected["market"][0][2], 12)

    def test_duplicate_sell_rows_share_one_pacing_allowance(self):
        selected = action([["SELL", "EGG", 2], ["SELL", "EGG", 10]])
        result, report = transform(
            observation(shed={"EGG": 12}), CFG, selected, mode="conservative_ahead")
        self.assertTrue(report["changed"])
        self.assertEqual(result["market"], [["SELL", "EGG", 2], ["SELL", "EGG", 1]])

    def test_aggressive_behind_accelerates_only_already_selected_stock(self):
        selected = action([["SELL", "WOOL", 2], ["SELL", "WOOL", 1],
                           ["SELL", "MILK", 1]])
        obs = observation(own_money=4000, rival_money=9000,
                          shed={"WOOL": 7, "MILK": 0})
        result, report = transform(obs, CFG, selected, mode="adaptive")
        self.assertTrue(report["changed"])
        self.assertEqual(report["mode"], "aggressive_behind")
        self.assertEqual(result["market"], [["SELL", "WOOL", 7], ["SELL", "WOOL", 0],
                                            ["SELL", "MILK", 1]])
        self.assertEqual([row[1] for row in result["market"]],
                         [row[1] for row in selected["market"]])

    def test_visible_rival_liquidation_blocks_ahead_hold(self):
        rival_tiles = [[None] * 10 for _ in range(10)]
        rival_tiles[0][0] = {"kind": "PASTURE", "animal": "COW", "yield_units": 10}
        selected = action([["SELL", "EGG", 12]])
        obs = observation(own_money=7000, rival_money=6000, shed={"EGG": 12},
                          rival_tiles=rival_tiles, prices={"MILK": 160})
        result, report = transform(obs, CFG, selected, mode="adaptive")
        self.assertIs(result, selected)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "no_margin_trigger")
        self.assertEqual(report["rival_visible_liquidation_bound"], 1600.0)

    def test_malformed_sell_fails_closed(self):
        selected = action([["SELL", "EGG", "12"], ["SELL", "WOOL", 1]])
        result, report = transform(observation(shed={"EGG": 12, "WOOL": 1}),
                                   CFG, selected, mode="adaptive")
        self.assertIs(result, selected)
        self.assertEqual(report["reason"], "malformed_sell")

    def test_malformed_rival_tile_fails_closed(self):
        rival_tiles = [[None] * 10 for _ in range(10)]
        rival_tiles[0][0] = "unexpected"
        selected = action([["SELL", "EGG", 12]])
        result, report = transform(observation(shed={"EGG": 12}, rival_tiles=rival_tiles),
                                   CFG, selected, mode="adaptive")
        self.assertIs(result, selected)
        self.assertEqual(report["reason"], "malformed_rival_tiles")

    def test_no_realizable_stock_is_identity(self):
        selected = action([["SELL", "EGG", 4]])
        result, report = transform(observation(shed={"EGG": 0}), CFG, selected,
                                   mode="aggressive_behind")
        self.assertIs(result, selected)
        self.assertFalse(report["changed"])

    def test_final_action_is_never_rewritten(self):
        selected = action([["SELL", "EGG", 12]])
        result, report = transform(observation(step=718, shed={"EGG": 12}),
                                   CFG, selected, mode="adaptive")
        self.assertIs(result, selected)
        self.assertEqual(report["reason"], "terminal_step_identity")

    def test_outside_late_window_is_identity(self):
        selected = action([["SELL", "EGG", 12]])
        result, report = transform(observation(step=650, shed={"EGG": 12}),
                                   CFG, selected, mode="adaptive")
        self.assertIs(result, selected)
        self.assertEqual(report["reason"], "outside_late_window")

    def test_market_prefix_cap_preserves_suffix(self):
        rows = [["SELL", "EGG", 1] for _ in range(11)]
        selected = action(rows)
        cfg = dict(CFG, maxMarketOrdersPerTurn=10)
        result, report = transform(observation(shed={"EGG": 20}), cfg, selected,
                                   mode="conservative_ahead")
        self.assertTrue(report["changed"])
        self.assertEqual(result["market"][10], ["SELL", "EGG", 1])
        self.assertEqual(len(result["market"]), len(selected["market"]))

    def test_forced_modes_do_not_cross_activate(self):
        selected = action([["SELL", "EGG", 12]])
        ahead = observation(own_money=10000, rival_money=5000, shed={"EGG": 12})
        behind = observation(own_money=4000, rival_money=9000, shed={"EGG": 12})
        result, report = transform(ahead, CFG, selected, mode="aggressive_behind")
        self.assertIs(result, selected)
        self.assertEqual(report["reason"], "no_margin_trigger")
        result, report = transform(behind, CFG, selected, mode="conservative_ahead")
        self.assertIs(result, selected)
        self.assertEqual(report["reason"], "no_margin_trigger")


if __name__ == "__main__":
    unittest.main()
