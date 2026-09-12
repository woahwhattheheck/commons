#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest
from copy import deepcopy

import shop_first


def obs(*, step=200, shops=None, shed=None):
    return {
        "step": step,
        "town": {"unlocked_shops": [] if shops is None else list(shops)},
        "private": {"shed": {} if shed is None else dict(shed)},
    }


def action(*rows):
    return {"farmer": ["PASS"], "hands": [], "market": [list(row) for row in rows]}


class ShopFirstLiveCanaryTests(unittest.TestCase):
    def test_non_callback_is_identity(self):
        selected = action(["SELL", "EGG", 5])
        out, report = shop_first.apply(
            obs(step=201, shops=["BAKERY"], shed={"EGG": 5, "WHEAT": 0}), selected
        )
        self.assertIs(out, selected)
        self.assertEqual(report["status"], "not_shop_callback")

    def test_no_shop_demand_is_identity(self):
        selected = action(["SELL", "EGG", 5])
        out, report = shop_first.apply(obs(shops=[], shed={"EGG": 5}), selected)
        self.assertIs(out, selected)
        self.assertEqual(report["status"], "no_unlocked_shop_demand")

    def test_bakery_holds_one_egg_only_when_baseline_would_exhaust_it(self):
        selected = action(["SELL", "EGG", 5], ["SELL", "WHEAT", 2])
        original = deepcopy(selected)
        out, report = shop_first.apply(
            obs(shops=["BAKERY"], shed={"EGG": 5, "WHEAT": 7}), selected
        )
        self.assertEqual(out["market"], [["SELL", "EGG", 4], ["SELL", "WHEAT", 2]])
        self.assertEqual(selected, original)
        self.assertEqual(report["reductions"], {"EGG": 1})
        self.assertTrue(report["live_only"])

    def test_yarn_store_single_product_multiplier_holds_two(self):
        selected = action(["SELL", "WOOL", 4])
        out, report = shop_first.apply(
            obs(shops=["YARN_STORE"], shed={"WOOL": 4}), selected
        )
        self.assertEqual(out["market"], [["SELL", "WOOL", 2]])
        self.assertEqual(report["demand"], {"WOOL": 2})
        self.assertEqual(report["reductions"], {"WOOL": 2})

    def test_duplicate_shops_accumulate_visible_demand(self):
        selected = action(["SELL", "WOOL", 6])
        out, report = shop_first.apply(
            obs(shops=["YARN_STORE", "YARN_STORE"], shed={"WOOL": 6}), selected
        )
        self.assertEqual(report["demand"], {"WOOL": 4})
        self.assertEqual(out["market"], [["SELL", "WOOL", 2]])

    def test_existing_unsold_inventory_needs_no_edit(self):
        selected = action(["SELL", "EGG", 3])
        out, report = shop_first.apply(
            obs(shops=["BAKERY"], shed={"EGG": 10, "WHEAT": 0}), selected
        )
        self.assertIs(out, selected)
        self.assertEqual(report["status"], "reserve_already_preserved")

    def test_full_row_deletion_requirement_fails_closed(self):
        selected = action(["SELL", "EGG", 1], ["BUY_SEED", "WHEAT", 3])
        original = deepcopy(selected)
        out, report = shop_first.apply(
            obs(shops=["BAKERY"], shed={"EGG": 1, "WHEAT": 0}), selected
        )
        self.assertIs(out, selected)
        self.assertEqual(out, original)
        self.assertEqual(report["status"], "row_deletion_required")

    def test_reductions_keep_every_row_positive_and_preserve_positions(self):
        selected = action(["SELL", "WOOL", 2], ["BUY_SEED", "WHEAT", 1], ["SELL", "WOOL", 2])
        out, report = shop_first.apply(
            obs(shops=["YARN_STORE"], shed={"WOOL": 4}), selected
        )
        self.assertEqual(
            out["market"],
            [["SELL", "WOOL", 1], ["BUY_SEED", "WHEAT", 1], ["SELL", "WOOL", 1]],
        )
        self.assertEqual([row["row_index"] for row in report["edited_rows"]], [2, 0])

    def test_capped_suffix_is_not_counted_or_shifted(self):
        selected = action(
            ["SELL", "EGG", 3],
            ["BUY_SEED", "WHEAT", 1],
            ["SELL", "EGG", 99],
        )
        out, report = shop_first.apply(
            obs(shops=["BAKERY"], shed={"EGG": 3, "WHEAT": 0}),
            selected,
            {"maxMarketOrdersPerTurn": 2},
        )
        self.assertEqual(out["market"], [["SELL", "EGG", 2], ["BUY_SEED", "WHEAT", 1], ["SELL", "EGG", 99]])
        self.assertEqual(report["edited_rows"], [{"item": "EGG", "row_index": 0, "before": 3, "after": 2}])

    def test_unknown_shop_or_bad_config_is_identity(self):
        selected = action(["SELL", "EGG", 5])
        out, report = shop_first.apply(
            obs(shops=["FUTURE_SHOP"], shed={"EGG": 5}), selected
        )
        self.assertIs(out, selected)
        self.assertEqual(report["status"], "shop_shape_drift")
        out, report = shop_first.apply(
            obs(shops=["BAKERY"], shed={"EGG": 5, "WHEAT": 0}),
            selected,
            {"townShopSellInterval": True},
        )
        self.assertIs(out, selected)
        self.assertEqual(report["status"], "configuration_shape_drift")

    def test_malformed_relevant_sell_and_shed_quantity_fail_closed(self):
        selected = action(["SELL", "EGG", True])
        out, report = shop_first.apply(
            obs(shops=["BAKERY"], shed={"EGG": 5, "WHEAT": 0}), selected
        )
        self.assertIs(out, selected)
        self.assertEqual(report["status"], "sell_shape_drift")
        good = action(["SELL", "EGG", 5])
        out, report = shop_first.apply(
            obs(shops=["BAKERY"], shed={"EGG": True, "WHEAT": 0}), good
        )
        self.assertIs(out, good)
        self.assertEqual(report["status"], "shed_quantity_drift")


if __name__ == "__main__":
    unittest.main(verbosity=2)
