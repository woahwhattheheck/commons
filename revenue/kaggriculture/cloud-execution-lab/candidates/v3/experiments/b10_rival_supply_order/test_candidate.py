from __future__ import annotations

import copy
import unittest

import candidate as b10


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
    return {"farmer": ["PASS"], "hands": [], "market": [list(row) for row in rows]}


class RivalSupplyOrderTests(unittest.TestCase):
    def test_supply_lower_bound_exact_without_own_sell_or_town(self):
        previous = {item: 100 for item in b10.PRODUCTS}
        current = dict(previous)
        current["WOOL"] = 104
        zero = {item: 0 for item in b10.PRODUCTS}
        lower = b10._rival_supply_lower_bound(previous, current, zero, zero)
        self.assertEqual(lower["WOOL"], 4)

    def test_requested_own_sell_upper_cannot_fabricate_rival_supply(self):
        previous = {item: 100 for item in b10.PRODUCTS}
        current = dict(previous)
        current["MILK"] = 103
        town = {item: 0 for item in b10.PRODUCTS}
        own = {item: 0 for item in b10.PRODUCTS}
        own["MILK"] = 3
        lower = b10._rival_supply_lower_bound(previous, current, town, own)
        self.assertEqual(lower["MILK"], 0)

    def test_own_buy_only_hides_rival_supply(self):
        previous = {item: 100 for item in b10.PRODUCTS}
        current = dict(previous)
        current["EGG"] = 103
        zero = {item: 0 for item in b10.PRODUCTS}
        lower = b10._rival_supply_lower_bound(previous, current, zero, zero)
        self.assertEqual(lower["EGG"], 3)

    def test_town_consumption_handles_multi_and_single_product_shops(self):
        row = b10._town_consumption(obs(4, shops=["BAKERY", "YARN_STORE"]))
        self.assertEqual(row["WHEAT"], 1)
        self.assertEqual(row["EGG"], 1)
        self.assertEqual(row["WOOL"], 2)
        self.assertEqual(row["FERTILIZER"], 0)

    def test_town_center_consumption_is_added_at_step_24(self):
        row = b10._town_consumption(obs(24, shops=[]))
        for item in b10.CENTER_PRODUCTS:
            self.assertEqual(row[item], 1)
        self.assertEqual(row["FERTILIZER"], 0)

    def test_positive_supply_moves_product_earlier_inside_leading_sell_block(self):
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
        self.assertEqual([row[1] for row in result["market"][:3]], ["CARROT", "WOOL", "MILK"])
        self.assertEqual(result["market"][3], ["PASS"])
        self.assertEqual(detail["before"], ["MILK", "WOOL", "CARROT"])
        self.assertEqual(detail["after"], ["CARROT", "WOOL", "MILK"])

    def test_equal_supply_preserves_native_relative_order(self):
        parent = action(("SELL", "MILK", 2), ("SELL", "WOOL", 3), ("SELL", "CARROT", 1))
        evidence = {item: 0 for item in b10.PRODUCTS}
        evidence["MILK"] = evidence["WOOL"] = 2
        result, detail = b10._reorder_leading_sells(parent, evidence)
        self.assertIs(result, parent)
        self.assertIsNone(detail)

    def test_wheat_row_stays_at_exact_index(self):
        parent = action(
            ("SELL", "MILK", 2),
            ("SELL", "WHEAT", 5),
            ("SELL", "CARROT", 1),
            ("SELL", "WOOL", 1),
        )
        evidence = {item: 0 for item in b10.PRODUCTS}
        evidence["WOOL"] = 9
        evidence["CARROT"] = 3
        result, _ = b10._reorder_leading_sells(parent, evidence)
        self.assertEqual(result["market"][1], ["SELL", "WHEAT", 5])
        self.assertEqual([result["market"][i][1] for i in (0, 2, 3)], ["WOOL", "CARROT", "MILK"])

    def test_later_cash_spend_vetoes_reorder(self):
        parent = action(
            ("SELL", "MILK", 2),
            ("SELL", "WOOL", 3),
            ("HIRE",),
        )
        evidence = {item: 0 for item in b10.PRODUCTS}
        evidence["WOOL"] = 9
        result, detail = b10._reorder_leading_sells(parent, evidence)
        self.assertIs(result, parent)
        self.assertIsNone(detail)

    def test_nonleading_sell_is_not_moved(self):
        parent = action(
            ("SELL", "MILK", 2),
            ("SELL", "WOOL", 3),
            ("PASS",),
            ("SELL", "CARROT", 9),
        )
        evidence = {item: 0 for item in b10.PRODUCTS}
        evidence["WOOL"] = 2
        evidence["CARROT"] = 99
        result, _ = b10._reorder_leading_sells(parent, evidence)
        self.assertEqual(result["market"][3], ["SELL", "CARROT", 9])

    def test_disabled_arm_is_exact_parent_identity(self):
        tracker = b10.RivalSupplyOrder(enabled=False)
        tracker.apply(obs(1), action())
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        current = obs(2, {"WOOL": 10_003})
        result = tracker.apply(current, parent)
        self.assertIs(result, parent)
        self.assertEqual(tracker.telemetry["confirmed_supply_transitions"], 1)
        self.assertEqual(tracker.telemetry["reorders"], 0)

    def test_gap_or_rewind_does_not_use_stale_supply_evidence(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        tracker.apply(obs(1), action())
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        result = tracker.apply(obs(3, {"WOOL": 10_050}), parent)
        self.assertIs(result, parent)
        self.assertEqual(tracker.telemetry["reorders"], 0)

    def test_unknown_shop_fails_closed_and_drops_state(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        result = tracker.apply(obs(4, shops=["UNKNOWN"]), parent)
        self.assertIs(result, parent)
        self.assertEqual(tracker.players, {})

    def test_custom_market_params_disable_mutation(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        tracker.apply(obs(1), action())
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        current = obs(2, {"WOOL": 10_003})
        result = tracker.apply(current, parent, {"marketParams": {"WOOL": {"base": 999}}})
        self.assertIs(result, parent)

    def test_bool_sell_quantity_is_malformed_not_one(self):
        with self.assertRaises(ValueError):
            b10._own_sell_upper(action(("SELL", "WOOL", True)))

    def test_no_positive_evidence_keeps_exact_parent(self):
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        evidence = {item: -5 for item in b10.PRODUCTS}
        result, detail = b10._reorder_leading_sells(parent, evidence)
        self.assertIs(result, parent)
        self.assertIsNone(detail)

    def test_nonstandard_or_ambiguous_market_cap_fails_closed_and_clears_latch(self):
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        for cap in (1, 3, 0, -1, True, 10.0, "10", 11):
            with self.subTest(cap=cap):
                tracker = b10.RivalSupplyOrder(enabled=True)
                tracker.apply(obs(1), action())
                self.assertIn(0, tracker.players)
                result = tracker.apply(
                    obs(2, {"WOOL": 10_003}),
                    parent,
                    {"maxMarketOrdersPerTurn": cap},
                )
                self.assertIs(result, parent)
                self.assertEqual(tracker.players, {})
                self.assertEqual(tracker.telemetry["reorders"], 0)

    def test_invalid_player_never_seeds_or_uses_tracker_state(self):
        tracker = b10.RivalSupplyOrder(enabled=True)
        parent = action(("SELL", "MILK", 1), ("SELL", "WOOL", 1))
        self.assertIs(tracker.apply(obs(1, player=2), parent), parent)
        self.assertIs(tracker.apply(obs(2, {"WOOL": 10_003}, player=2), parent), parent)
        self.assertEqual(tracker.players, {})
        self.assertEqual(tracker.telemetry["reorders"], 0)


if __name__ == "__main__":
    unittest.main()
