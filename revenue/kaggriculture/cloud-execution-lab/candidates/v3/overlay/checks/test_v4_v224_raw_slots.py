# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 ``r04_v224_raw_slots``.

Run in a materialised candidate package:

    python -B -m unittest -v checks/test_v4_v224_raw_slots.py
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
import r04_v224_raw_slots as lane  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10,
          "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
          "farmHandCostMult": 1}


def action(market):
    return {"farmer": ["PASS"], "hands": [], "market": copy.deepcopy(market)}


def observation(step=0):
    tiles = [["LOCKED"] * 10 for _ in range(10)]
    farm = {"tiles": tiles, "farmer": [4, 4], "hands": [], "money": 1000,
            "unlocked_quadrants": ["NW"], "hires_today": 0}
    prices = {product: 10 for product in r04.PRODUCTS}
    inventory = {product: 10000 for product in r04.PRODUCTS}
    return {"step": step, "day": step // 24, "hour": step % 24, "player": 0,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"inventories": [{}], "shed": {}, "seeds": {}},
            "market": {"prices": prices, "inventory": inventory},
            "town": {"unlocked_shops": []}}


def _official_milk_price(inventory):
    """Pinned engine MILK quote for inventory >= I0 (engine blob 3c202c7e...)."""
    base = 160
    i0 = 10000
    target = 1.60
    production_window = 122
    assert inventory >= i0
    amp = target * base / production_window
    return max(1, int(round(base - amp * (inventory - i0))))


def _official_lockstep_milk_sales(own_market, rival_market):
    """Execute the pinned engine's SELL/MILK lockstep subset.

    This is deliberately tiny: it preserves the official `_process_market`
    contract that raw list indices define rounds, both players quote from the
    same pre-commit inventory in a round, and successful sales then increase
    market inventory. Each player begins with two MILK, enough for this witness.
    """
    queues = [list(own_market), list(rival_market)]
    cash = [0, 0]
    shed = [2, 2]
    inventory = 10000

    for row_index in range(max(len(queue) for queue in queues)):
        remaining = [0, 0]
        for player_id, queue in enumerate(queues):
            if row_index >= len(queue):
                continue
            row = queue[row_index]
            if (isinstance(row, list) and len(row) >= 3
                    and row[0] == "SELL" and row[1] == "MILK"
                    and type(row[2]) is int and row[2] > 0):
                remaining[player_id] = row[2]

        while any(remaining):
            # Official engine quotes both current units before either commit.
            quote = _official_milk_price(inventory)
            quotes = [quote if remaining[player_id] else None for player_id in range(2)]
            committed = False
            for player_id, price in enumerate(quotes):
                if price is None:
                    continue
                if shed[player_id] <= 0:
                    remaining[player_id] = 0
                    continue
                shed[player_id] -= 1
                cash[player_id] += price
                if price > 1:
                    inventory += 1
                remaining[player_id] -= 1
                committed = True
            if not committed:
                break

    return cash, inventory


class V224RawSlots(unittest.TestCase):
    def tearDown(self):
        r04.V224_RAW_SLOTS = False

    def test_key_ships_off_and_features_accept_it(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_v224_raw_slots"], False)
        self.assertIs(Features(**data).r04_v224_raw_slots, False)

    def test_falsey_slot_is_hard_barrier_and_parent_object_is_retained(self):
        parent = action([["HIRE"], [], ["SELL", "WOOL", 2]])
        out = lane.sales_first_raw_slots(parent)
        self.assertIs(out, parent)
        self.assertEqual(out["market"], [["HIRE"], [], ["SELL", "WOOL", 2]])

    def test_none_slot_is_hard_barrier(self):
        parent = action([["HIRE"], None, ["SELL", "WOOL", 2]])
        self.assertIs(lane.sales_first_raw_slots(parent), parent)

    def test_sell_bubbles_across_contiguous_effectful_rows(self):
        parent = action([["HIRE"], ["BUY_SEED", "WHEAT", 1], ["SELL", "WOOL", 2]])
        out = lane.sales_first_raw_slots(parent)
        self.assertIsNot(out, parent)
        self.assertEqual(out["market"],
                         [["SELL", "WOOL", 2], ["HIRE"], ["BUY_SEED", "WHEAT", 1]])
        self.assertEqual(parent["market"],
                         [["HIRE"], ["BUY_SEED", "WHEAT", 1], ["SELL", "WOOL", 2]])

    def test_same_item_product_buy_remains_barrier(self):
        parent = action([["HIRE"], ["BUY_PRODUCT", "WOOL", 1], ["SELL", "WOOL", 2]])
        self.assertIs(lane.sales_first_raw_slots(parent), parent)

    def test_unrelated_product_buy_keeps_v224_crossing_semantics(self):
        parent = action([["BUY_PRODUCT", "WHEAT", 1], ["SELL", "WOOL", 2]])
        out = lane.sales_first_raw_slots(parent)
        self.assertEqual(out["market"],
                         [["SELL", "WOOL", 2], ["BUY_PRODUCT", "WHEAT", 1]])

    def test_zero_quantity_and_malformed_rows_are_barriers(self):
        for barrier in (["BUY_SEED", "WHEAT", 0], ["BUY_SEED"], "bad"):
            parent = action([["HIRE"], barrier, ["SELL", "WOOL", 2]])
            with self.subTest(barrier=barrier):
                self.assertIs(lane.sales_first_raw_slots(parent), parent)

    def test_unknown_positive_verb_is_malformed_barrier(self):
        parent = action([["HIRE"], ["BOGUS", "WOOL", 1], ["SELL", "WOOL", 2]])
        out = lane.sales_first_raw_slots(parent)
        self.assertIs(out, parent)
        self.assertEqual(out["market"],
                         [["HIRE"], ["BOGUS", "WOOL", 1], ["SELL", "WOOL", 2]])

    def test_changed_prefix_retains_raw_cardinality(self):
        parent = action([["HIRE"], ["SELL", "WOOL", 2], [],
                         ["BUY_SEED", "WHEAT", 1], ["SELL", "MILK", 3]])
        out = lane.sales_first_raw_slots(parent)
        self.assertEqual(len(out["market"]), len(parent["market"]))
        self.assertEqual(out["market"][2], [])
        self.assertEqual(out["market"],
                         [["SELL", "WOOL", 2], ["HIRE"], [],
                          ["SELL", "MILK", 3], ["BUY_SEED", "WHEAT", 1]])

    def test_router_flag_off_preserves_frozen_v224_compaction(self):
        parent = action([[], ["SELL", "WOOL", 2]])
        r04.V224_RAW_SLOTS = False
        out = r04._v224_sales_first(copy.deepcopy(parent))
        self.assertEqual(out["market"], [["SELL", "WOOL", 2]])

    def test_router_flag_on_prevents_falsey_compaction(self):
        parent = action([[], ["SELL", "WOOL", 2]])
        r04.V224_RAW_SLOTS = True
        out = r04._v224_sales_first(parent)
        self.assertIs(out, parent)
        self.assertEqual(out["market"], [[], ["SELL", "WOOL", 2]])

    def test_raw_slot_changes_lockstep_receipt_against_rival_sell(self):
        # Rival sells MILK in row 0. With the authored None barrier our SELL is
        # row 1 and sees the post-rival inventory; frozen V224 compaction moves
        # it into row 0, where both players quote from the same pre-commit state.
        parent = action([None, ["SELL", "MILK", 1]])
        rival = [["SELL", "MILK", 1], None]

        r04.V224_RAW_SLOTS = False
        compacted = r04._v224_sales_first(copy.deepcopy(parent))
        self.assertEqual(compacted["market"], [["SELL", "MILK", 1]])

        r04.V224_RAW_SLOTS = True
        preserved = r04._v224_sales_first(parent)
        self.assertIs(preserved, parent)
        self.assertEqual(preserved["market"], [None, ["SELL", "MILK", 1]])

        compact_cash, compact_inventory = _official_lockstep_milk_sales(
            compacted["market"], rival)
        preserved_cash, preserved_inventory = _official_lockstep_milk_sales(
            preserved["market"], rival)

        self.assertEqual(compact_cash[0], 160)
        self.assertEqual(preserved_cash[0], 158)
        self.assertEqual(compact_inventory, 10002)
        self.assertEqual(preserved_inventory, 10002)
        self.assertGreater(compact_cash[0], preserved_cash[0])

    def test_install_and_titan_diagnostics_carry_key(self):
        r04.install(v224_raw_slots=True)
        self.assertIs(r04.V224_RAW_SLOTS, True)
        r04.install(v224_raw_slots=False)
        self.assertIs(r04.V224_RAW_SLOTS, False)

        agent = TitanAgent(Features(r04_sale_window=True, r04_v224_raw_slots=True))
        agent.act(observation(), dict(CONFIG))
        self.assertIs(r04.V224_RAW_SLOTS, True)
        self.assertIs(agent.diagnostics["v224_raw_slots"], True)


if __name__ == "__main__":
    unittest.main()
