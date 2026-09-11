# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 ``r04_b10_public_supply_order``."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_b10_public_supply_order as b10  # noqa: E402
import r04_full_router as r04  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {
    "episodeSteps": 720,
    "turnsPerDay": 24,
    "townShopUnlockInterval": 3,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
    "boardSize": 10,
    "farmHandCostMult": 1,
}


def obs(step: int, inventory=None, *, shops=None, player: int = 0):
    values = {item: 10_000 for item in b10.PRODUCTS}
    if inventory:
        values.update(inventory)
    return {
        "step": step,
        "player": player,
        "market": {"inventory": values},
        "town": {"unlocked_shops": list(shops or [])},
    }


def action(*rows):
    market = []
    for row in rows:
        market.append(list(row) if isinstance(row, tuple) else row)
    return {"farmer": ["PASS"], "hands": [], "market": market}


def shops_for_step(step: int):
    count = min(8, (step // 24) // 3)
    return ["YARN_STORE"] * count


def full_observation(step=0):
    tiles = [["LOCKED"] * 10 for _ in range(10)]
    for y in range(3, 7):
        for x in range(3, 7):
            tiles[y][x] = {"kind": "SOIL"}
    farm = {
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [],
        "money": 3000,
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    prices = {item: 10 for item in r04.PRODUCTS}
    inventory = {item: 10_000 for item in r04.PRODUCTS}
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [farm, copy.deepcopy(farm)],
        "private": {"inventories": [{}], "shed": {}},
        "market": {"prices": prices, "inventory": inventory},
        "town": {"unlocked_shops": shops_for_step(step)},
    }


class RivalSupplyOrderTests(unittest.TestCase):
    def tearDown(self):
        if hasattr(r04, "B10_PUBLIC_SUPPLY_ORDER"):
            r04.B10_PUBLIC_SUPPLY_ORDER = False
        b10.ORDER.players.clear()

    def test_key_ships_off_and_features_accept_it(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_b10_public_supply_order"], False)
        self.assertIs(data["r04_place_delivery"], False)
        features = Features(**data)
        self.assertIs(features.r04_b10_public_supply_order, False)
        self.assertIs(features.r04_place_delivery, False)

    def test_supply_lower_bound_exact(self):
        previous = {item: 100 for item in b10.PRODUCTS}
        current = dict(previous)
        current["WOOL"] = 104
        zero = {item: 0 for item in b10.PRODUCTS}
        lower = b10._rival_supply_lower_bound(previous, current, zero, zero)
        self.assertEqual(lower["WOOL"], 4)

    def test_town_consumption_handles_single_and_multi_product_shops(self):
        row = b10._town_consumption(
            obs(4, shops=["BAKERY", "YARN_STORE"]), dict(CONFIG)
        )
        self.assertEqual(row["WHEAT"], 1)
        self.assertEqual(row["EGG"], 1)
        self.assertEqual(row["WOOL"], 2)
        self.assertEqual(row["FERTILIZER"], 0)

    def test_positive_supply_reorders_only_movable_leading_sells(self):
        parent = action(
            ("SELL", "MILK", 2),
            ("SELL", "WOOL", 3),
            ("SELL", "CARROT", 1),
            ("PASS",),
        )
        evidence = {item: 0 for item in b10.PRODUCTS}
        evidence["CARROT"] = 4
        evidence["WOOL"] = 2
        result, detail = b10._reorder_leading_sells(parent, evidence)
        self.assertIsNot(result, parent)
        self.assertEqual(
            [row[1] for row in result["market"][:3]],
            ["CARROT", "WOOL", "MILK"],
        )
        self.assertEqual(result["market"][3], ["PASS"])
        self.assertEqual(detail["before"], ["MILK", "WOOL", "CARROT"])

    def test_wheat_and_fertilizer_rows_are_pinned_at_exact_indices(self):
        parent = action(
            ("SELL", "MILK", 1),
            ("SELL", "WHEAT", 1),
            ("SELL", "CARROT", 1),
            ("SELL", "FERTILIZER", 1),
            ("SELL", "WOOL", 1),
        )
        evidence = {item: 0 for item in b10.PRODUCTS}
        evidence.update({"WOOL": 9, "CARROT": 3, "MILK": 1, "FERTILIZER": 99})
        result, detail = b10._reorder_leading_sells(parent, evidence)
        self.assertIsNotNone(detail)
        self.assertEqual(result["market"][1], ["SELL", "WHEAT", 1])
        self.assertEqual(result["market"][3], ["SELL", "FERTILIZER", 1])
        self.assertEqual(
            [result["market"][i][1] for i in (0, 2, 4)],
            ["WOOL", "CARROT", "MILK"],
        )

    def test_tuple_sell_lookalike_is_a_noop_barrier(self):
        parent = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "MILK", 1], ("SELL", "WOOL", 1)],
        }
        evidence = {item: 0 for item in b10.PRODUCTS}
        evidence["WOOL"] = 9
        result, detail = b10._reorder_leading_sells(parent, evidence)
        self.assertIs(result, parent)
        self.assertIsNone(detail)

    def test_later_cash_spend_vetoes_reorder(self):
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1), ("HIRE",))
        evidence = {item: 0 for item in b10.PRODUCTS}
        evidence["WOOL"] = 9
        result, detail = b10._reorder_leading_sells(parent, evidence)
        self.assertIs(result, parent)
        self.assertIsNone(detail)

    def test_valid_step0_then_step1_signal_reorders(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        empty = action()
        self.assertIs(tracker.apply(obs(0), empty, dict(CONFIG)), empty)

        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        result = tracker.apply(obs(1, {"WOOL": 10_002}), parent, dict(CONFIG))
        self.assertIsNot(result, parent)
        self.assertEqual(
            result["market"][:2],
            [["SELL", "WOOL", 1], ["SELL", "MILK", 1]],
        )

    def test_disabled_helper_is_exact_parent_identity(self):
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        self.assertIs(
            b10.apply_public_supply_order(
                obs(0), parent, dict(CONFIG), enabled=False
            ),
            parent,
        )

    def test_terminal_step_718_records_but_never_reorders(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        empty = action()
        for step in range(0, 718):
            result = tracker.apply(
                obs(step, shops=shops_for_step(step)),
                empty,
                dict(CONFIG),
            )
            self.assertIs(result, empty)

        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        result = tracker.apply(
            obs(718, {"WOOL": 10_002}, shops=shops_for_step(718)),
            parent,
            dict(CONFIG),
        )
        self.assertIs(result, parent)
        self.assertEqual(tracker.players[0]["step"], 718)
        self.assertEqual(tracker.telemetry["reorders"], 0)

    def test_engine_unreachable_step_719_drops_latch(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        tracker.apply(obs(0), action(), dict(CONFIG))
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        result = tracker.apply(
            obs(719, shops=shops_for_step(719)), parent, dict(CONFIG)
        )
        self.assertIs(result, parent)
        self.assertEqual(tracker.players, {})

    def test_install_and_titan_diagnostics_carry_key(self):
        r04.install(None, 8, 0, False, False, b10_public_supply_order=True)
        self.assertIs(r04.B10_PUBLIC_SUPPLY_ORDER, True)
        r04.install(None, 8, 0, False, False, b10_public_supply_order=False)
        self.assertIs(r04.B10_PUBLIC_SUPPLY_ORDER, False)

        agent = TitanAgent(
            Features(r04_sale_window=True, r04_b10_public_supply_order=True)
        )
        agent.act(full_observation(step=0), dict(CONFIG))
        self.assertIs(r04.B10_PUBLIC_SUPPLY_ORDER, True)
        self.assertIs(agent.diagnostics["b10_public_supply_order"], True)

    def test_b10_is_outermost_over_final_parent_action(self):
        original_core = r04._v3_core
        flags = {
            name: getattr(r04, name)
            for name in (
                "MIRROR_HORIZON",
                "TERMINAL_FERTILIZER",
                "GOOSE_RESCUE",
                "PLACE_DELIVERY",
                "GOOSE_PASS_RESCUE",
                "B10_PUBLIC_SUPPLY_ORDER",
            )
        }
        try:
            parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
            r04._v3_core = lambda observation, configuration=None: parent
            r04.MIRROR_HORIZON = False
            r04.TERMINAL_FERTILIZER = False
            r04.GOOSE_RESCUE = False
            r04.PLACE_DELIVERY = False
            r04.GOOSE_PASS_RESCUE = False
            r04.B10_PUBLIC_SUPPLY_ORDER = True
            b10.ORDER.players.clear()

            self.assertIs(r04.v3_agent(obs(0), dict(CONFIG)), parent)
            out = r04.v3_agent(obs(1, {"WOOL": 10_002}), dict(CONFIG))
            self.assertIsNot(out, parent)
            self.assertEqual(
                out["market"][:2],
                [["SELL", "WOOL", 1], ["SELL", "MILK", 1]],
            )
        finally:
            r04._v3_core = original_core
            for name, value in flags.items():
                setattr(r04, name, value)


if __name__ == "__main__":
    unittest.main()
