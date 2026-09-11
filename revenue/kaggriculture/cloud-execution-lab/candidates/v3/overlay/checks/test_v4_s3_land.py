# SPDX-License-Identifier: Apache-2.0
"""V4 lane S3 (key r04_s3_land, overlay/r04_s3_land.py): open the SE quadrant.

    python -m unittest -v checks/test_v4_s3_land.py

Covers the shipped-off config and Features default, TitanAgent wiring, v3_agent() identity with the
key off, every guard on the SE BUY_LAND (owned quadrants, allowed day and hours, last step, cash plus
reserve, a queued BUY_LAND, a full market, raw falsey slots, malformed state), and the helpers the SE
operator reads (se_tiles, se_open, se_empty, shop_draw_tonight). Standard library only.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
import r04_s3_land as s3  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10, "shedCapacity": 100,
          "maxMarketOrdersPerTurn": 10, "farmHandCostMult": 1}

DAY12 = 12 * 24          # step 288, hour 0 of a day with day % 3 == 0


def grid(owned=("NW", "NE", "SW")):
    def quadrant(x, y):
        return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")
    return [[{"kind": "PLANT", "crop": "WHEAT"} if quadrant(x, y) in owned else "LOCKED"
             for x in range(10)] for y in range(10)]


def observation(step=DAY12, owned=("NW", "NE", "SW"), money=7000.0, shops=3, tiles=None, town=None):
    farm = {"tiles": tiles if tiles is not None else grid(owned), "farmer": [4, 4], "hands": [],
            "money": money, "unlocked_quadrants": list(owned), "hires_today": 0}
    return {"step": step, "day": step // 24, "hour": step % 24, "player": 0,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"inventories": [{}], "shed": {"WHEAT": 5}, "seeds": {}},
            "market": {"prices": {product: 40 for product in r04.PRODUCTS}, "inventory": {}},
            "town": {"unlocked_shops": list(town) if town is not None else ["PET_CAFE"] * shops}}


def action(market=None):
    return {"farmer": ["PASS"], "hands": [],
            "market": [["SELL", "WHEAT", 3]] if market is None else market}


def reset():
    r04.S3_LAND = False
    s3.S3_LAND = False
    for key in ("calls", "buy_requests", "skip_cash", "skip_full", "skip_v219"):
        s3.REPORT[key] = 0
    s3.REPORT["buy_step"] = None
    s3.DEFER_TO_V219 = True
    r04.MIRROR_HORIZON = False
    r04.TERMINAL_FERTILIZER = False
    r04.GOOSE_RESCUE = False
    r04._TERMINAL_FERTILIZER_AGENT = None
    r04.FERT_HAND = False
    r04._FERT_HAND_AGENT = None
    r04.ROW_SHED = False
    r04.ROW_ORDER = False
    r04.EVENING_FLUSH = False
    r04.STRAWBERRY_TOPUP = False
    r04.B5_CARROT_FERTILIZER = False
    r04.B5_JIT_FERTILIZE = False
    r04.DRIBBLE_DUMP = False
    r04.NO_LATE_SALE_ADVANCE = False
    r04.NO_LATE_SALE_ADVANCE_STEP = 648


class ShippedKey(unittest.TestCase):
    def tearDown(self):
        reset()

    def test_key_ships_off(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_s3_land"], False)
        self.assertIs(Features(**data).r04_s3_land, False)
        self.assertIs(Features().r04_s3_land, False)

    def test_titan_passes_the_key_to_the_router(self):
        for on in (True, False):
            agent = TitanAgent(Features(r04_sale_window=True, r04_s3_land=on))
            agent.act(observation(), dict(CONFIG))
            self.assertIs(r04.S3_LAND, on)
            self.assertIs(agent.diagnostics["s3_land"], on)

    def test_v3_agent_is_the_lane_stack_while_the_key_is_off(self):
        saved = r04.POLICY_AGENT
        try:
            r04.POLICY_AGENT = lambda obs, cfg=None: copy.deepcopy(action())
            r04.install(None, 8, 0, False, False, s3_land=False)
            self.assertEqual(r04.v3_agent(observation(), dict(CONFIG)), action())
            r04.install(None, 8, 0, False, False, s3_land=True)
            self.assertEqual(r04.v3_agent(observation(), dict(CONFIG))["market"],
                             [["SELL", "WHEAT", 3], ["BUY_LAND"]])
        finally:
            r04.POLICY_AGENT = saved


class Purchase(unittest.TestCase):
    def setUp(self):
        s3.S3_LAND = True

    def tearDown(self):
        reset()

    def test_buys_se_after_ne_and_sw(self):
        out = s3.apply_s3_land(observation(), action())
        self.assertEqual(out["market"], [["SELL", "WHEAT", 3], ["BUY_LAND"]])
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertEqual(s3.REPORT["buy_step"], DAY12)

    def test_input_action_is_not_mutated(self):
        original = action()
        s3.apply_s3_land(observation(), original)
        self.assertEqual(original, action())

    def test_only_when_ne_and_sw_are_owned(self):
        for owned in (("NW",), ("NW", "NE"), ("NW", "NE", "SW", "SE")):
            a = action()
            self.assertIs(s3.apply_s3_land(observation(owned=owned), a), a, owned)

    def test_only_in_early_hours_of_a_day_divisible_by_three(self):
        for step in (DAY12 + s3.BUY_HOURS, 13 * 24, 14 * 24, 11 * 24 + 2):
            a = action()
            self.assertIs(s3.apply_s3_land(observation(step=step), a), a, step)
        for step in (DAY12, DAY12 + s3.BUY_HOURS - 1, 15 * 24, 18 * 24 + s3.V219_REQUEST_HOURS):
            self.assertEqual(s3.apply_s3_land(observation(step=step), action())["market"][-1], ["BUY_LAND"], step)

    def test_not_after_the_last_step(self):
        a = action()
        self.assertIs(s3.apply_s3_land(observation(step=21 * 24), a), a)

    def test_cash_must_cover_se_and_the_reserve(self):
        a = action()
        self.assertIs(s3.apply_s3_land(observation(money=s3.SE_PRICE + s3.RESERVE - 1), a), a)
        self.assertEqual(s3.REPORT["skip_cash"], 1)
        out = s3.apply_s3_land(observation(money=s3.SE_PRICE + s3.RESERVE), action())
        self.assertEqual(out["market"][-1], ["BUY_LAND"])

    def test_never_doubles_a_queued_buy_land(self):
        a = action([["BUY_LAND"], ["SELL", "WHEAT", 3]])
        self.assertIs(s3.apply_s3_land(observation(), a), a)

    def test_never_exceeds_the_order_cap(self):
        a = action([["SELL", "WHEAT", 1]] * s3.MAX_ORDERS)
        self.assertIs(s3.apply_s3_land(observation(), a), a)
        self.assertEqual(s3.REPORT["skip_full"], 1)

    def test_raw_falsey_slots_keep_their_indexes(self):
        out = s3.apply_s3_land(observation(), action([["SELL", "WOOL", 2], None, ["SELL", "MILK", 1]]))
        self.assertEqual(out["market"], [["SELL", "WOOL", 2], None, ["SELL", "MILK", 1], ["BUY_LAND"]])

    def test_empty_or_missing_market(self):
        self.assertEqual(s3.apply_s3_land(observation(), action([]))["market"], [["BUY_LAND"]])
        bare = {"farmer": ["PASS"], "hands": []}
        self.assertEqual(s3.apply_s3_land(observation(), bare)["market"], [["BUY_LAND"]])

    def test_malformed_state_fails_closed(self):
        for obs in ({}, {"step": DAY12}, {"step": "x", "player": 0, "farms": []},
                    {"step": DAY12, "player": 3, "farms": [{}]}):
            a = action()
            self.assertIs(s3.apply_s3_land(obs, a), a)
        for bad in (None, "PASS", {"market": "SELL"}):
            self.assertIs(s3.apply_s3_land(observation(), bad), bad)

    def test_key_off_is_identity(self):
        s3.S3_LAND = False
        a = action()
        self.assertIs(s3.apply_s3_land(observation(), a), a)


class DeferToV219(unittest.TestCase):
    """V219's day-18 tomato program buys SE itself; S3 waits while it can still qualify."""

    def setUp(self):
        s3.S3_LAND = True

    def tearDown(self):
        reset()

    def test_day12_waits_when_two_more_shop_nights_could_reach_three(self):
        town = ["PET_CAFE", "PIZZA_SHOP", "BAKERY", "YARN_STORE"]
        a = action()
        self.assertIs(s3.apply_s3_land(observation(town=town), a), a)
        self.assertEqual(s3.REPORT["skip_v219"], 1)

    def test_day12_buys_with_none_of_the_v219_shops(self):
        town = ["PET_CAFE", "BAKERY", "YARN_STORE", "SMOOTHIE_SHOP"]
        self.assertEqual(s3.apply_s3_land(observation(town=town), action())["market"][-1], ["BUY_LAND"])

    def test_day15_one_night_left(self):
        one = ["PET_CAFE", "FARMERS_MARKET", "BAKERY", "YARN_STORE", "SMOOTHIE_SHOP"]
        two = ["PIZZA_SHOP", "FARMERS_MARKET", "BAKERY", "YARN_STORE", "SMOOTHIE_SHOP"]
        self.assertEqual(s3.apply_s3_land(observation(step=15 * 24, town=one), action())["market"][-1],
                         ["BUY_LAND"])
        a = action()
        self.assertIs(s3.apply_s3_land(observation(step=15 * 24, town=two), a), a)

    def test_day18_stays_out_of_v219_request_hours(self):
        for hour in range(s3.V219_REQUEST_HOURS):
            a = action()
            self.assertIs(s3.apply_s3_land(observation(step=18 * 24 + hour), a), a, hour)

    def test_day18_buys_after_v219_left_se_locked(self):
        town = ["PIZZA_SHOP", "FARMERS_MARKET", "PIZZA_SHOP", "BAKERY", "YARN_STORE", "PET_CAFE"]
        obs = observation(step=18 * 24 + s3.V219_REQUEST_HOURS, town=town)
        self.assertEqual(s3.apply_s3_land(obs, action())["market"][-1], ["BUY_LAND"])

    def test_defer_off(self):
        s3.DEFER_TO_V219 = False
        town = ["PIZZA_SHOP", "FARMERS_MARKET", "BAKERY", "YARN_STORE"]
        self.assertEqual(s3.apply_s3_land(observation(town=town), action())["market"][-1], ["BUY_LAND"])

    def test_v219_possible(self):
        self.assertTrue(s3.v219_possible(observation(step=9 * 24, town=["PET_CAFE"] * 3)))
        self.assertFalse(s3.v219_possible(observation(step=DAY12, town=["PET_CAFE"] * 4)))
        self.assertTrue(s3.v219_possible(observation(step=DAY12, town=["PIZZA_SHOP"] + ["PET_CAFE"] * 3)))
        self.assertFalse(s3.v219_possible(observation(step=18 * 24, town=["PIZZA_SHOP"] * 2 + ["PET_CAFE"] * 4)))
        self.assertTrue(s3.v219_possible(observation(step=18 * 24, town=["PIZZA_SHOP"] * 3 + ["PET_CAFE"] * 3)))
        self.assertFalse(s3.v219_possible(observation(step=19 * 24, town=["PIZZA_SHOP"] * 5)))


class OperatorHelpers(unittest.TestCase):
    def tearDown(self):
        reset()

    def test_se_tiles_follow_the_engine_quadrant_rule(self):
        tiles = s3.se_tiles(10)
        self.assertEqual(len(tiles), 25)
        self.assertTrue(all(x >= 5 and y >= 5 for x, y in tiles))

    def test_se_open(self):
        self.assertFalse(s3.se_open(observation()))
        self.assertTrue(s3.se_open(observation(owned=("NW", "NE", "SW", "SE"))))
        self.assertFalse(s3.se_open({}))

    def test_se_empty_counts_only_empty_se_tiles(self):
        tiles = grid(("NW", "NE", "SW", "SE"))
        tiles[7][6] = None
        tiles[9][9] = None
        tiles[1][1] = None      # NW empty tile is not SE
        tiles[8][8] = {"kind": "WEED"}
        obs = observation(owned=("NW", "NE", "SW", "SE"), tiles=tiles)
        self.assertEqual(sorted(s3.se_empty(obs)), [(6, 7), (9, 9)])

    def test_shop_draw_tonight(self):
        self.assertTrue(s3.shop_draw_tonight(observation(step=11 * 24 + 5, shops=3)))
        self.assertTrue(s3.shop_draw_tonight(observation(step=2 * 24, shops=0)))
        self.assertFalse(s3.shop_draw_tonight(observation(step=DAY12, shops=4)))
        self.assertFalse(s3.shop_draw_tonight(observation(step=13 * 24, shops=4)))
        self.assertFalse(s3.shop_draw_tonight(observation(step=26 * 24, shops=8)))


if __name__ == "__main__":
    unittest.main()
