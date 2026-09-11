import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_e5_floor_liquidation as e5


def standard_config(**overrides):
    cfg = {
        "episodeSteps": 720,
        "turnsPerDay": 24,
        "maxMarketOrdersPerTurn": 10,
        "shedCapacity": 100,
        "townShopSellInterval": 4,
        "townCenterSellInterval": 24,
    }
    cfg.update(overrides)
    return cfg


def observation(step=717, shed=None, prices=None, farmer_inventory=None):
    shed = dict(shed or {})
    all_prices = {item: 2 for item in e5.r04.PRODUCTS}
    all_prices.update(prices or {})
    tiles = [[None for _ in range(10)] for _ in range(10)]
    return {
        "step": step,
        "player": 0,
        "farms": [{
            "tiles": tiles,
            "farmer": [4, 4],
            "hands": [],
        }],
        "private": {
            "inventories": [dict(farmer_inventory or {})],
            "shed": shed,
        },
        "market": {"prices": all_prices},
        "town": {"unlocked_shops": []},
    }


class FloorLiquidationTests(unittest.TestCase):
    def setUp(self):
        e5.ENABLED = True
        e5.reset_report()

    def test_disabled_is_exact_identity(self):
        e5.ENABLED = False
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        self.assertIs(action, e5.apply_floor_liquidation(
            observation(shed={"CARROT": 5}, prices={"CARROT": 1}),
            standard_config(),
            action,
        ))

    def test_only_penultimate_step_can_change(self):
        for step in (716, 718):
            with self.subTest(step=step):
                action = {"farmer": ["PASS"], "hands": [], "market": []}
                self.assertIs(action, e5.apply_floor_liquidation(
                    observation(step=step, shed={"CARROT": 5}, prices={"CARROT": 1}),
                    standard_config(),
                    action,
                ))

    def test_floor_safe_item_appends_without_mutating_parent_rows(self):
        parent_row = ["BUY_SEED", "WHEAT", 1]
        action = {"farmer": ["PASS"], "hands": [], "market": [parent_row]}
        result = e5.apply_floor_liquidation(
            observation(shed={"CARROT": 5}, prices={"CARROT": 1}),
            standard_config(),
            action,
        )
        self.assertIsNot(result, action)
        self.assertEqual([parent_row, ["SELL", "CARROT", 5]], result["market"])
        self.assertEqual([parent_row], action["market"])
        self.assertIs(parent_row, result["market"][0])

    def test_existing_sale_is_residualized_and_left_unchanged(self):
        parent = ["SELL", "MILK", 2]
        action = {"farmer": ["PASS"], "hands": [], "market": [parent]}
        result = e5.apply_floor_liquidation(
            observation(shed={"MILK": 5}, prices={"MILK": 1}),
            standard_config(),
            action,
        )
        self.assertEqual([parent, ["SELL", "MILK", 3]], result["market"])
        self.assertEqual(["SELL", "MILK", 2], parent)

    def test_wheat_and_fertilizer_are_never_added(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        result = e5.apply_floor_liquidation(
            observation(
                shed={"WHEAT": 8, "FERTILIZER": 9},
                prices={"WHEAT": 1, "FERTILIZER": 1},
            ),
            standard_config(),
            action,
        )
        self.assertIs(result, action)

    def test_price_above_floor_keeps_parent(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        result = e5.apply_floor_liquidation(
            observation(shed={"WOOL": 7}, prices={"WOOL": 2}),
            standard_config(),
            action,
        )
        self.assertIs(result, action)

    def test_order_cap_only_uses_remaining_slots(self):
        rows = [["BUY_SEED", "WHEAT", 1] for _ in range(9)]
        action = {"farmer": ["PASS"], "hands": [], "market": rows}
        result = e5.apply_floor_liquidation(
            observation(
                shed={"CARROT": 3, "TOMATO": 4},
                prices={"CARROT": 1, "TOMATO": 1},
            ),
            standard_config(),
            action,
        )
        self.assertEqual(10, len(result["market"]))
        self.assertEqual(["SELL", "CARROT", 3], result["market"][-1])

    def test_nonstandard_or_type_confused_configuration_fails_closed(self):
        cases = [
            {"townShopSellInterval": 3},
            {"episodeSteps": 719},
            {"turnsPerDay": 24.0},
            {"maxMarketOrdersPerTurn": True},
            {"shedCapacity": "100"},
        ]
        for override in cases:
            with self.subTest(override=override):
                action = {"farmer": ["PASS"], "hands": [], "market": []}
                self.assertIs(action, e5.apply_floor_liquidation(
                    observation(shed={"EGG": 4}, prices={"EGG": 1}),
                    standard_config(**override),
                    action,
                ))

    def test_missing_configuration_proof_fails_closed(self):
        full = standard_config()
        partial = dict(full)
        partial.pop("townCenterSellInterval")
        cases = [None, {}, partial]
        for configuration in cases:
            with self.subTest(configuration=configuration):
                action = {"farmer": ["PASS"], "hands": [], "market": []}
                self.assertIs(action, e5.apply_floor_liquidation(
                    observation(shed={"EGG": 4}, prices={"EGG": 1}),
                    configuration,
                    action,
                ))

    def test_malformed_existing_same_item_sell_fails_closed(self):
        for row in (["SELL", "EGG"], ["SELL", "EGG", 1.0], ["SELL", "EGG", True]):
            with self.subTest(row=row):
                action = {"farmer": ["PASS"], "hands": [], "market": [row]}
                self.assertIs(action, e5.apply_floor_liquidation(
                    observation(shed={"EGG": 4}, prices={"EGG": 1}),
                    standard_config(),
                    action,
                ))

    def test_report_tracks_only_actual_additions(self):
        action = {"farmer": ["PASS"], "hands": [], "market": []}
        e5.apply_floor_liquidation(
            observation(shed={"CARROT": 2, "WOOL": 3}, prices={"CARROT": 1, "WOOL": 1}),
            standard_config(),
            action,
        )
        self.assertEqual(1, e5.REPORT["activations"])
        self.assertEqual(2, e5.REPORT["rows_added"])
        self.assertEqual(5, e5.REPORT["quantity_added"])


if __name__ == "__main__":
    unittest.main()
