# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

import mirror_collision_value as C

HERE = Path(__file__).resolve().parent
MARKET_BASELINE_PATH = HERE.parents[2] / "research" / "market-baseline" / "market_baseline.py"
SPEC = importlib.util.spec_from_file_location("rowshed_market_baseline", MARKET_BASELINE_PATH)
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


class MirrorCollisionValueTests(unittest.TestCase):
    def test_price_authority_is_same_official_engine_blob(self):
        self.assertEqual(M.ENGINE_BLOB_SHA, C.ENGINE_GIT_BLOB)
        self.assertEqual(C.ENGINE_GIT_BLOB, "3c202c7ee921da239356789e266b694635103fc4")

    def test_carrot_exact_early_vs_late_value(self):
        got = C.mirror_collision_score(
            item="CARROT", public_inventory=10_000, fillable=5, price_fn=M.market_price
        )
        self.assertEqual(got["early_cash"], 168)
        self.assertEqual(got["late_cash"], 160)
        self.assertEqual(got["exact_mirror_collision_value"], 8)
        self.assertEqual(got["incumbent_endpoint_score"], 15)

    def test_wool_exact_early_vs_late_value(self):
        got = C.mirror_collision_score(
            item="WOOL", public_inventory=10_000, fillable=5, price_fn=M.market_price
        )
        self.assertEqual(got["early_cash"], 998)
        self.assertEqual(got["late_cash"], 985)
        self.assertEqual(got["exact_mirror_collision_value"], 13)
        self.assertEqual(got["incumbent_endpoint_score"], 5)

    def test_official_curves_exhibit_rowshed_rank_inversion(self):
        report = C.analyze_rows(
            [
                {"item": "CARROT", "public_inventory": 10_000, "fillable": 5},
                {"item": "WOOL", "public_inventory": 10_000, "fillable": 5},
            ],
            price_fn=M.market_price,
        )
        self.assertEqual(report["incumbent_rank_indices"], [0, 1])
        self.assertEqual(report["mirror_rank_indices"], [1, 0])
        self.assertTrue(report["rank_diverges"])

    def test_loss_forensics_melon_wool_inversion(self):
        report = C.analyze_rows(
            [
                {"item": "MELON", "public_inventory": 10_025, "fillable": 60},
                {"item": "WOOL", "public_inventory": 10_025, "fillable": 30},
            ],
            price_fn=M.market_price,
        )
        melon, wool = report["scores"]
        self.assertEqual(melon["incumbent_endpoint_score"], 3960)
        self.assertEqual(melon["exact_mirror_collision_value"], 6083)
        self.assertEqual(wool["incumbent_endpoint_score"], 4200)
        self.assertEqual(wool["exact_mirror_collision_value"], 3071)
        self.assertEqual(report["incumbent_rank_indices"], [1, 0])
        self.assertEqual(report["mirror_rank_indices"], [0, 1])
        self.assertEqual(
            melon["exact_mirror_collision_value"] - wool["exact_mirror_collision_value"],
            3012,
        )

    def test_stable_ties_preserve_input_order(self):
        rows = [
            {"item": "WHEAT", "public_inventory": 10_000, "fillable": 3},
            {"item": "WHEAT", "public_inventory": 10_000, "fillable": 3},
        ]
        report = C.analyze_rows(rows, price_fn=M.market_price)
        self.assertEqual(report["incumbent_rank_indices"], [0, 1])
        self.assertEqual(report["mirror_rank_indices"], [0, 1])
        self.assertFalse(report["rank_diverges"])

    def test_price_floor_sales_do_not_advance_inventory(self):
        def floor_price(_item, inventory):
            return 2 if inventory < 5 else 1

        got = C.mirror_collision_score(
            item="X", public_inventory=4, fillable=3, price_fn=floor_price
        )
        self.assertEqual(got["early_cash"], 4)
        self.assertEqual(got["late_cash"], 3)
        self.assertEqual(got["after_our_lot_inventory"], 5)
        self.assertEqual(got["exact_mirror_collision_value"], 1)

    def test_bool_and_zero_poison_fail_closed(self):
        for inventory, fillable in ((True, 1), (10_000, True), (10_000, 0)):
            with self.subTest(inventory=inventory, fillable=fillable):
                with self.assertRaises(C.MirrorCollisionInputError):
                    C.mirror_collision_score(
                        item="WHEAT",
                        public_inventory=inventory,
                        fillable=fillable,
                        price_fn=M.market_price,
                    )

    def test_unit_loop_escape_bound_fails_closed(self):
        self.assertEqual(C.MAX_EXECUTABLE_UNITS_PER_MARKET_ORDER, 99_999)
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_collision_score(
                item="WHEAT",
                public_inventory=10_000,
                fillable=100_000,
                price_fn=M.market_price,
            )

    def test_unknown_product_fails_closed(self):
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_collision_score(
                item="NOT_A_PRODUCT",
                public_inventory=10_000,
                fillable=1,
                price_fn=M.market_price,
            )

    def test_non_integer_price_fails_closed(self):
        with self.assertRaises(C.MirrorCollisionInputError):
            C.mirror_collision_score(
                item="X",
                public_inventory=0,
                fillable=1,
                price_fn=lambda _item, _inventory: 1.5,
            )

    def test_row_schema_drift_fails_closed(self):
        with self.assertRaises(C.MirrorCollisionInputError):
            C.analyze_rows(
                [
                    {"item": "WHEAT", "public_inventory": 10_000, "fillable": 3, "extra": 1},
                    {"item": "WOOL", "public_inventory": 10_000, "fillable": 3},
                ],
                price_fn=M.market_price,
            )

    def test_reports_are_research_only_and_never_mutate_actions(self):
        report = C.analyze_rows(
            [
                {"item": "CARROT", "public_inventory": 10_000, "fillable": 5},
                {"item": "WOOL", "public_inventory": 10_000, "fillable": 5},
            ],
            price_fn=M.market_price,
        )
        self.assertTrue(report["research_only"])
        self.assertFalse(report["decision_authority"])
        self.assertFalse(report["action_mutation_authority"])
        self.assertFalse(report["rival_action_prediction"])
        self.assertNotIn("action", report)


if __name__ == "__main__":
    unittest.main()
