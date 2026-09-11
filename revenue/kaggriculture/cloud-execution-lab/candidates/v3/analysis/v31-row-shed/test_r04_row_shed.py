# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
OVERLAY = V3 / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import compose_current_root as composer  # noqa: E402
import r04_row_shed as row_shed  # noqa: E402
import r04_full_router as r04  # noqa: E402


class RowShedContract(unittest.TestCase):
    def test_requested_thousand_is_ranked_by_actual_stock(self):
        market = [
            ["SELL", "MELON", 1000],
            ["SELL", "WOOL", 50],
            ["HIRE"],
            ["SELL", "MILK", 3],
        ]
        self.assertEqual(r04.order_sells(market, {})[0], ["SELL", "MELON", 1000])

        ordered = row_shed.order_leading_sells(
            market, {}, {"MELON": 1, "WOOL": 50}, r04._ro_price
        )
        self.assertEqual(ordered[:2], [["SELL", "WOOL", 50], ["SELL", "MELON", 1000]])
        self.assertEqual(ordered[2:], [["HIRE"], ["SELL", "MILK", 3]])
        self.assertEqual(sorted(map(repr, ordered[:2])), sorted(map(repr, market[:2])))

    def test_effective_quantity_is_min_requested_and_projected(self):
        self.assertEqual(row_shed.effective_sell_quantity(["SELL", "MILK", 1000], {"MILK": 8}), 8)
        self.assertEqual(row_shed.effective_sell_quantity(["SELL", "MILK", 4], {"MILK": 8}), 4)
        self.assertEqual(row_shed.effective_sell_quantity(["SELL", "MILK", 4], {"MILK": 0}), 0)

    def test_missing_or_malformed_projection_falls_back_to_requested(self):
        order = ["SELL", "MILK", 4]
        self.assertEqual(row_shed.effective_sell_quantity(order, {}), 4)
        self.assertEqual(row_shed.effective_sell_quantity(order, None), 4)
        for bad in (True, 3.0, "3", -1, None):
            with self.subTest(bad=bad):
                self.assertEqual(row_shed.effective_sell_quantity(order, {"MILK": bad}), 4)

    def test_poisoned_projection_reproduces_incumbent_requested_quantity_order(self):
        market = [["SELL", "MELON", 1000], ["SELL", "WOOL", 50], ["HIRE"]]
        incumbent = r04.order_sells(market, {})
        for projected in ({}, None, {"WOOL": "50"}, {"MELON": -1, "WOOL": True}):
            with self.subTest(projected=projected):
                self.assertEqual(
                    row_shed.order_leading_sells(market, {}, projected, r04._ro_price), incumbent
                )

    def test_equal_scores_keep_incumbent_order(self):
        market = [["SELL", "MILK", 1000], ["SELL", "WOOL", 1000], ["HIRE"]]
        ordered = row_shed.order_leading_sells(market, {}, {"MILK": 0, "WOOL": 0}, r04._ro_price)
        self.assertEqual(ordered, market)

    def test_only_contiguous_leading_sell_block_can_move(self):
        market = [["SELL", "MELON", 1000], ["SELL", "WOOL", 50], [], ["SELL", "MILK", 1000]]
        ordered = row_shed.order_leading_sells(
            market, {}, {"MELON": 1, "WOOL": 50, "MILK": 1000}, r04._ro_price
        )
        self.assertEqual(ordered[2:], market[2:])
        self.assertEqual(ordered[:2], [["SELL", "WOOL", 50], ["SELL", "MELON", 1000]])

    def test_malformed_requested_quantity_fails_closed(self):
        for bad in (True, 3.0, "3", -1, None):
            with self.subTest(bad=bad):
                market = [["SELL", "MELON", 1000], ["SELL", "WOOL", bad], ["HIRE"]]
                self.assertIs(
                    row_shed.order_leading_sells(market, {}, {"MELON": 5, "WOOL": 5}, r04._ro_price),
                    market,
                )

    def test_failed_price_model_fails_closed(self):
        market = [["SELL", "MELON", 1000], ["SELL", "WOOL", 50]]
        def broken(*_args):
            raise RuntimeError("no trusted default curve")
        self.assertIs(row_shed.order_leading_sells(market, {}, {"MELON": 5, "WOOL": 5}, broken), market)


class ComposerContract(unittest.TestCase):
    def setUp(self):
        self.r04_path = V3 / "overlay" / "r04_full_router.py"
        self.apply_path = V3 / "apply_v3.py"
        self.r04_before = self.r04_path.read_text(encoding="utf-8")
        self.apply_before = self.apply_path.read_text(encoding="utf-8")

    def test_composer_patches_exact_current_root_without_writing(self):
        r04_after = composer.patch_r04(self.r04_before)
        apply_after = composer.patch_apply(self.apply_before)

        self.assertIn("ROW_SHED = False", r04_after)
        self.assertIn("b5_carrot_fertilizer=None, b5_jit_fertilize=None, row_shed=None", r04_after)
        self.assertIn("global B5_CARROT_FERTILIZER, B5_JIT_FERTILIZE, ROW_SHED", r04_after)
        self.assertIn("Fail closed to the incumbent requested-quantity score", r04_after)
        self.assertIn("r04_row_shed", apply_after)
        self.assertIn("bool(self.features.r04_b5_jit_fertilize),\\n", apply_after)
        self.assertIn("bool(self.features.r04_row_shed))(observation, configuration)", apply_after)

        self.assertEqual(self.r04_path.read_text(encoding="utf-8"), self.r04_before)
        self.assertEqual(self.apply_path.read_text(encoding="utf-8"), self.apply_before)

    def test_composer_refuses_double_application(self):
        with self.assertRaises(RuntimeError):
            composer.patch_r04(composer.patch_r04(self.r04_before))
        with self.assertRaises(RuntimeError):
            composer.patch_apply(composer.patch_apply(self.apply_before))

    def test_existing_b5_jit_and_l3_markers_survive_patch(self):
        after = composer.patch_r04(self.r04_before)
        for marker in (
            "B5_CARROT_FERTILIZER = False",
            "B5_JIT_FERTILIZE = False",
            "NO_LATE_SALE_ADVANCE_STEP = 648",
            "SALE_EXCLUDED = ('WHEAT', 'FERTILIZER')",
        ):
            self.assertEqual(after.count(marker), self.r04_before.count(marker), marker)


if __name__ == "__main__":
    unittest.main()
