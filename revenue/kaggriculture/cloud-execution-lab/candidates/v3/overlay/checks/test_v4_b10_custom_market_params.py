# SPDX-License-Identifier: Apache-2.0
"""Regression checks for B10 fail-closed reachability edges."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_b10_public_supply_order as b10  # noqa: E402
import r04_full_router as r04  # noqa: E402

CONFIG = {
    "episodeSteps": 720,
    "maxMarketOrdersPerTurn": 10,
    "shedCapacity": 100,
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


def previous_record(*, inventory=None, town=None, own=None, step=0, shops=()):
    values = {item: 10_000 for item in b10.PRODUCTS}
    if inventory:
        values.update(inventory)
    drains = {item: 0 for item in b10.PRODUCTS}
    if town:
        drains.update(town)
    upper = {item: 0 for item in b10.PRODUCTS}
    if own:
        upper.update(own)
    return {
        "step": step,
        "inventory": values,
        "shops": tuple(shops),
        "town_consume": drains,
        "own_sell_upper": upper,
    }


class B10ReachabilityEdges(unittest.TestCase):
    def tearDown(self):
        if hasattr(r04, "B10_PUBLIC_SUPPLY_ORDER"):
            r04.B10_PUBLIC_SUPPLY_ORDER = False
        b10.ORDER.players.clear()

    def test_only_valid_step0_can_seed_epoch(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))

        self.assertIs(tracker.apply(obs(7), parent, dict(CONFIG)), parent)
        self.assertEqual(tracker.players, {})

        malformed = obs(0, {"WOOL": 9_999})
        self.assertIs(tracker.apply(malformed, parent, dict(CONFIG)), parent)
        self.assertEqual(tracker.players, {})

        empty = action()
        self.assertIs(tracker.apply(obs(0), empty, dict(CONFIG)), empty)
        self.assertEqual(tracker.players[0]["step"], 0)

    def test_valid_step0_replaces_stale_process_state(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        tracker.players[0] = previous_record(step=718)
        empty = action()
        self.assertIs(tracker.apply(obs(0), empty, dict(CONFIG)), empty)
        self.assertEqual(tracker.players[0]["step"], 0)
        self.assertEqual(tracker.players[0]["inventory"]["WOOL"], 10_000)

    def test_gap_drops_epoch_and_retry_cannot_reseed(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        empty = action()
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        tracker.apply(obs(0), empty, dict(CONFIG))

        self.assertIs(
            tracker.apply(obs(2, {"WOOL": 10_003}), parent, dict(CONFIG)),
            parent,
        )
        self.assertEqual(tracker.players, {})

        self.assertIs(
            tracker.apply(obs(2, {"WOOL": 10_003}), parent, dict(CONFIG)),
            parent,
        )
        self.assertEqual(tracker.players, {})
        self.assertEqual(tracker.telemetry["reorders"], 0)

    def test_missing_configuration_breaks_epoch_and_retry_cannot_reseed(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        tracker.apply(obs(0), action(), dict(CONFIG))
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))

        self.assertIs(tracker.apply(obs(1, {"WOOL": 10_002}), parent, None), parent)
        self.assertEqual(tracker.players, {})

        self.assertIs(
            tracker.apply(obs(1, {"WOOL": 10_002}), parent, dict(CONFIG)),
            parent,
        )
        self.assertEqual(tracker.players, {})

    def test_falsey_or_nonempty_market_params_clear_epoch(self):
        bad_values = ([], "", 0, False, {"WOOL": {"base": 999}})
        for bad in bad_values:
            with self.subTest(value=bad):
                tracker = b10.RivalSupplyOrder(enabled=True)
                tracker.apply(obs(0), action(), dict(CONFIG))
                cfg = dict(CONFIG)
                cfg["marketParams"] = bad
                parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
                self.assertIs(tracker.apply(obs(1), parent, cfg), parent)
                self.assertEqual(tracker.players, {})

    def test_empty_market_params_mapping_keeps_standard_path(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        cfg = dict(CONFIG)
        cfg["marketParams"] = {}
        tracker.apply(obs(0), action(), cfg)
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        out = tracker.apply(obs(1, {"WOOL": 10_002}), parent, cfg)
        self.assertEqual(
            out["market"][:2],
            [["SELL", "WOOL", 1], ["SELL", "MILK", 1]],
        )

    def test_configuration_types_and_standard_shed_capacity_are_strict(self):
        bad_cases = (
            ("episodeSteps", 719),
            ("episodeSteps", True),
            ("episodeSteps", 720.0),
            ("maxMarketOrdersPerTurn", 9),
            ("maxMarketOrdersPerTurn", True),
            ("shedCapacity", 99),
            ("shedCapacity", 101),
            ("shedCapacity", True),
            ("shedCapacity", 100.0),
        )
        for key, value in bad_cases:
            with self.subTest(key=key, value=value):
                tracker = b10.RivalSupplyOrder(enabled=True)
                tracker.apply(obs(0), action(), dict(CONFIG))
                cfg = dict(CONFIG)
                cfg[key] = value
                parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
                self.assertIs(tracker.apply(obs(1), parent, cfg), parent)
                self.assertEqual(tracker.players, {})

    def test_cadence_values_are_strict_positive_json_ints(self):
        with self.assertRaises(ValueError):
            b10._expected_shop_count(72, {"turnsPerDay": True})
        with self.assertRaises(ValueError):
            b10._expected_shop_count(72, {"townShopUnlockInterval": 3.0})
        with self.assertRaises(ValueError):
            b10._expected_shop_count(72, {"townShopUnlockInterval": 0})

    def test_shop_count_and_prefix_are_exact(self):
        b10._validate_shop_snapshot(71, (), dict(CONFIG))
        b10._validate_shop_snapshot(72, ("YARN_STORE",), dict(CONFIG))
        with self.assertRaises(ValueError):
            b10._validate_shop_snapshot(71, ("YARN_STORE",), dict(CONFIG))
        with self.assertRaises(ValueError):
            b10._validate_shop_snapshot(
                72, ("YARN_STORE", "BAKERY"), dict(CONFIG)
            )
        b10._validate_shop_transition(72, 73, ("YARN_STORE",), ("YARN_STORE",))
        with self.assertRaises(ValueError):
            b10._validate_shop_transition(
                72, 73, ("YARN_STORE",), ("BAKERY",)
            )

    def test_tuple_sell_does_not_mask_rival_lower_bound(self):
        tuple_action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [("SELL", "CARROT", 100)],
        }
        self.assertEqual(b10._own_sell_upper(tuple_action)["CARROT"], 0)
        self.assertEqual(
            b10._own_sell_upper(action(("SELL", "CARROT", 100)))["CARROT"],
            100,
        )

    def test_nonbuyable_positive_gross_budget_200_control_and_201_poison(self):
        previous = previous_record(own={"CARROT": 50, "TOMATO": 50})
        current = dict(previous["inventory"])
        current.update({"CARROT": 10_100, "TOMATO": 10_100})
        evidence = b10._transition_evidence(previous, current, 100)
        self.assertEqual(evidence["CARROT"], 50)
        self.assertEqual(evidence["TOMATO"], 50)

        poisoned = dict(current)
        poisoned["CARROT"] = 10_101
        with self.assertRaises(ValueError):
            b10._transition_evidence(previous, poisoned, 100)

    def test_rival_lower_budget_100_control_and_101_poison(self):
        previous = previous_record()
        current = dict(previous["inventory"])
        current["CARROT"] = 10_100
        evidence = b10._transition_evidence(previous, current, 100)
        self.assertEqual(evidence["CARROT"], 100)

        poisoned = dict(previous["inventory"])
        poisoned["CARROT"] = 10_101
        with self.assertRaises(ValueError):
            b10._transition_evidence(previous, poisoned, 100)

    def test_nonbuyable_price_floor_room_is_exact_near_wool_boundary(self):
        self.assertEqual(
            b10._max_visible_nonbuyable_supply("WOOL", 10_058, 100), 1
        )
        self.assertEqual(
            b10._max_visible_nonbuyable_supply("WOOL", 10_059, 100), 0
        )
        self.assertEqual(
            b10._max_visible_nonbuyable_supply("WOOL", 10_060, 100), 0
        )

        previous = previous_record(inventory={"WOOL": 10_059})
        current = dict(previous["inventory"])
        current["WOOL"] = 10_060
        with self.assertRaises(ValueError):
            b10._transition_evidence(previous, current, 100)

    def test_near_floor_one_unit_transition_can_be_reached_from_step0(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        empty = action()
        tracker.apply(obs(0), empty, dict(CONFIG))

        # Step-0 town center drains one WOOL after the market, so a step-1
        # observation of 10058 reconstructs gross=59 and reaches the last
        # pre-floor quoted inventory.
        self.assertIs(
            tracker.apply(obs(1, {"WOOL": 10_058}), empty, dict(CONFIG)),
            empty,
        )
        self.assertEqual(tracker.players[0]["inventory"]["WOOL"], 10_058)

        self.assertIs(
            tracker.apply(obs(2, {"WOOL": 10_059}), empty, dict(CONFIG)),
            empty,
        )
        self.assertEqual(tracker.players[0]["inventory"]["WOOL"], 10_059)

        self.assertIs(
            tracker.apply(obs(3, {"WOOL": 10_060}), empty, dict(CONFIG)),
            empty,
        )
        self.assertEqual(tracker.players, {})

    def test_buyable_history_cannot_authorize_b10_movement(self):
        previous = previous_record()
        current = dict(previous["inventory"])
        current["FERTILIZER"] = 50_000
        evidence = b10._transition_evidence(previous, current, 100)
        self.assertEqual(evidence["FERTILIZER"], 0)
        self.assertEqual(evidence["WHEAT"], 0)

        parent = action(
            ("SELL", "MILK", 1),
            ("SELL", "FERTILIZER", 1),
            ("SELL", "WOOL", 1),
        )
        evidence["WOOL"] = 5
        evidence["FERTILIZER"] = 999
        result, _ = b10._reorder_leading_sells(parent, evidence)
        self.assertEqual(result["market"][1], ["SELL", "FERTILIZER", 1])

    def test_unidentifiable_player_clears_all_latches(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        tracker.apply(obs(0, player=0), action(), dict(CONFIG))
        tracker.apply(obs(0, player=1), action(), dict(CONFIG))
        self.assertEqual(set(tracker.players), {0, 1})

        malformed = obs(1)
        malformed["player"] = True
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        self.assertIs(tracker.apply(malformed, parent, dict(CONFIG)), parent)
        self.assertEqual(tracker.players, {})


if __name__ == "__main__":
    unittest.main()
