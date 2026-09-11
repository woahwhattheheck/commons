# SPDX-License-Identifier: Apache-2.0
"""V3.1 key `r04_row_shed`: ROW_ORDER prices each leading SELL row at the units it can sell.

    python -m unittest -v checks/test_v31_row_shed.py

order_sells() ranks the leading SELL block by the price drop each row causes. With the key on,
v3_agent() passes the projected shed stock and each row is priced at min(order quantity, shed),
so a tape row that asks for 1000 units but can fill 2 no longer outranks a row that clears real
units. The production seam must preserve the reviewed S33 donor contract: raw market slots and
tail indices are never compacted, and incomplete/type-poisoned projected-shed evidence falls
back coherently to incumbent requested-quantity ROW_ORDER for the whole leading block.
Standard library only.
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
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10, "shedCapacity": 100,
          "maxMarketOrdersPerTurn": 10, "farmHandCostMult": 1}


def synthetic_observation(step, shed):
    tiles = [["LOCKED"] * 10 for _ in range(10)]
    for y in range(3, 7):
        for x in range(3, 7):
            tiles[y][x] = {"kind": "SOIL"}
    farm = {"tiles": tiles, "farmer": [4, 4], "hands": [], "money": 1000,
            "unlocked_quadrants": ["NW"], "hires_today": 0}
    return {"step": step, "day": step // 24, "hour": step % 24, "player": 0,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"inventories": [{}], "shed": dict(shed)},
            "market": {"prices": {product: 10 for product in r04.PRODUCTS}, "inventory": {}},
            "town": {"unlocked_shops": ["BAKERY", "YARN_STORE"]}}


def reset():
    r04.ROW_SHED = False
    r04.ROW_ORDER = False
    r04.EVENING_FLUSH = False
    r04.STRAWBERRY_TOPUP = False
    r04.B5_CARROT_FERTILIZER = False
    r04.B5_JIT_FERTILIZE = False
    r04.NO_LATE_SALE_ADVANCE = False
    r04.NO_LATE_SALE_ADVANCE_STEP = 648
    r04.SALE_HORIZON = 8
    r04.OPEN_ROUNDTRIP = 0
    r04.SALE_EXCLUDED = ("WHEAT", "FERTILIZER")
    r04._V231_EARLY = False
    r04._RIVAL_TAPE.update(same=0, seen=0, last=-1)


class OrderSells(unittest.TestCase):
    MARKET = [["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["HIRE"], ["SELL", "EGG", 3]]

    def test_without_shed_rows_are_priced_at_the_order_quantity(self):
        self.assertEqual(r04.order_sells([list(o) for o in self.MARKET], {}),
                         [["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["HIRE"], ["SELL", "EGG", 3]])

    def test_with_shed_rows_are_priced_at_the_units_they_can_sell(self):
        ordered = r04.order_sells([list(o) for o in self.MARKET], {}, {"WOOL": 1, "MILK": 6})
        self.assertEqual(ordered, [["SELL", "MILK", 6], ["SELL", "WOOL", 1000], ["HIRE"], ["SELL", "EGG", 3]])

    def test_shed_changes_only_the_order_never_a_row(self):
        market = [["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["SELL", "STRAWBERRY", 40], ["BUY_SEED", "WHEAT", 3]]
        ordered = r04.order_sells([list(o) for o in market], {}, {"WOOL": 0, "MILK": 6, "STRAWBERRY": 2})
        self.assertEqual(sorted(map(tuple, ordered[:3])), sorted(map(tuple, market[:3])))
        self.assertEqual(ordered[3:], market[3:])

    def test_missing_projection_falls_back_for_the_whole_leading_block(self):
        market = [["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["HIRE"]]
        incumbent = r04.order_sells(copy.deepcopy(market), {})
        self.assertEqual(
            r04.order_sells(copy.deepcopy(market), {}, {"MILK": 6}),
            incumbent,
        )

    def test_type_poisoned_projection_falls_back_for_the_whole_leading_block(self):
        market = [["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["HIRE"]]
        incumbent = r04.order_sells(copy.deepcopy(market), {})
        for bad in (True, 1.0, "1"):
            with self.subTest(bad=bad):
                self.assertEqual(
                    r04.order_sells(copy.deepcopy(market), {}, {"WOOL": bad, "MILK": 6}),
                    incumbent,
                )

    def test_type_poisoned_requested_quantity_preserves_raw_parent_order(self):
        cases = (
            [["SELL", "WOOL", True], ["SELL", "MILK", 6], ["HIRE"]],
            [["SELL", "WOOL", 1000], ["SELL", "MILK", 6000.0], ["HIRE"]],
            [["SELL", "WOOL", 1000], ["SELL", "MILK", "6000"], ["HIRE"]],
        )
        for market in cases:
            with self.subTest(market=market):
                self.assertEqual(
                    r04.order_sells(copy.deepcopy(market), {}, {"WOOL": 1, "MILK": 6}),
                    market,
                )


class Wiring(unittest.TestCase):
    def tearDown(self):
        reset()

    def test_key_ships_on(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_row_shed"], True)
        self.assertIs(Features(**data).r04_row_shed, True)
        self.assertIs(Features().r04_row_shed, True)

    def test_titan_passes_the_key_to_the_router(self):
        for on in (True, False):
            agent = TitanAgent(Features(r04_sale_window=True, r04_row_shed=on))
            agent.act(synthetic_observation(0, {"WHEAT": 5}), dict(CONFIG))
            self.assertIs(r04.ROW_SHED, on)
            self.assertIs(agent.diagnostics["row_shed"], on)

    def test_v3_agent_uses_the_shed_only_while_the_key_is_on(self):
        saved = r04.POLICY_AGENT
        try:
            r04.POLICY_AGENT = lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [],
                                                      "market": [["SELL", "WOOL", 1000], ["SELL", "MILK", 6]]}
            obs = synthetic_observation(300, {"WOOL": 1, "MILK": 6})
            r04.install(None, 8, 0, True, False, row_shed=False)
            self.assertEqual(r04.v3_agent(obs, dict(CONFIG))["market"], [["SELL", "WOOL", 1000], ["SELL", "MILK", 6]])
            r04.install(None, 8, 0, True, False, row_shed=True)
            self.assertEqual(r04.v3_agent(obs, dict(CONFIG))["market"], [["SELL", "MILK", 6], ["SELL", "WOOL", 1000]])
        finally:
            r04.POLICY_AGENT = saved

    def test_row_shed_preserves_raw_falsey_barrier_and_tail_index(self):
        saved = r04.POLICY_AGENT
        try:
            r04.POLICY_AGENT = lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [],
                                                      "market": [["SELL", "WOOL", 1000], [], ["SELL", "MILK", 6]]}
            obs = synthetic_observation(300, {"WOOL": 1, "MILK": 6})
            r04.install(None, 8, 0, True, False, row_shed=True)
            self.assertEqual(
                r04.v3_agent(obs, dict(CONFIG))["market"],
                [["SELL", "WOOL", 1000], [], ["SELL", "MILK", 6]],
            )
        finally:
            r04.POLICY_AGENT = saved

    def test_row_order_off_ignores_the_key(self):
        saved = r04.POLICY_AGENT
        try:
            r04.POLICY_AGENT = lambda obs, cfg=None: {"farmer": ["PASS"], "hands": [],
                                                      "market": [["SELL", "WOOL", 1000], ["SELL", "MILK", 6]]}
            r04.install(None, 8, 0, False, False, row_shed=True)
            obs = synthetic_observation(300, {"WOOL": 1, "MILK": 6})
            self.assertEqual(r04.v3_agent(obs, dict(CONFIG))["market"], [["SELL", "WOOL", 1000], ["SELL", "MILK", 6]])
        finally:
            r04.POLICY_AGENT = saved


if __name__ == "__main__":
    unittest.main()
