# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

import slot_capacity as subject


class SlotCapacityTests(unittest.TestCase):
    def setUp(self):
        self.limit = 10
        self.holed = [
            ["BUY_LAND"],
            ["BUY_SEED", "WHEAT", 1],
            ["SELL", "MILK", 1],
            [],
            ["BUY_ANIMAL", "GOOSE", 1],
            ["BUY_PRODUCT", "WHEAT", 1],
            ["SELL", "EGG", 1],
            ["BUY_SEED", "CARROT", 1],
            ["HIRE"],
            ["SELL", "FERTILIZER", 1],
        ]

    def test_predecessor_false_full_but_executable_prefix_has_capacity(self):
        self.assertFalse(
            subject.legacy_can_schedule(self.holed, "CARROT", 4, self.limit)
        )
        self.assertTrue(
            subject.executable_can_schedule(self.holed, "CARROT", 4, self.limit)
        )

    def test_first_hole_is_reused_without_moving_live_rows(self):
        before = copy.deepcopy(self.holed)
        after, index = subject.place_additional_sale(
            before, "CARROT", 4, self.limit
        )
        self.assertEqual(index, 3)
        self.assertEqual(after[3], ["SELL", "CARROT", 4])
        self.assertEqual(len(after), len(before))
        for row_index in range(len(before)):
            if row_index != index:
                self.assertEqual(after[row_index], before[row_index])
        self.assertEqual(before, self.holed)

    def test_full_prefix_is_not_compacted_or_reordered(self):
        full = copy.deepcopy(self.holed)
        full[3] = ["SELL", "WOOL", 1]
        self.assertFalse(subject.executable_can_schedule(full, "CARROT", 4, 10))
        after, index = subject.place_additional_sale(full, "CARROT", 4, 10)
        self.assertIsNone(index)
        self.assertEqual(after, full)

    def test_hole_after_limit_is_not_capacity(self):
        full = copy.deepcopy(self.holed)
        full[3] = ["SELL", "WOOL", 1]
        full.append([])
        self.assertFalse(subject.executable_can_schedule(full, "CARROT", 4, 10))

    def test_inactive_same_item_sale_does_not_cover_quantity(self):
        full = copy.deepcopy(self.holed)
        full[3] = ["SELL", "WOOL", 1]
        full.append(["SELL", "CARROT", 4])
        self.assertTrue(subject.legacy_can_schedule(full, "CARROT", 4, 10))
        self.assertFalse(subject.executable_can_schedule(full, "CARROT", 4, 10))

    def test_active_same_item_sale_can_cover_without_new_slot(self):
        full = copy.deepcopy(self.holed)
        full[3] = ["SELL", "CARROT", 4]
        self.assertTrue(subject.executable_can_schedule(full, "CARROT", 4, 10))

    def test_short_queue_appends(self):
        short = self.holed[:3]
        after, index = subject.place_additional_sale(short, "CARROT", 4, 10)
        self.assertEqual(index, 3)
        self.assertEqual(after[-1], ["SELL", "CARROT", 4])

    def test_witness_is_predecessor_discriminating(self):
        report = subject.witness()
        self.assertEqual(report["verdict"], "PREDECESSOR_FALSE_FULL_CONFIRMED")
        self.assertFalse(report["predecessor"]["can_schedule"])
        self.assertTrue(report["candidate"]["can_schedule"])
        self.assertTrue(report["controls"]["full_prefix_rejected"])
        self.assertTrue(report["controls"]["suffix_only_hole_rejected"])
        self.assertTrue(report["controls"]["inactive_same_item_not_counted"])

    def test_bool_quantity_and_limit_are_rejected(self):
        with self.assertRaises(subject.SlotCapacityError):
            subject.executable_can_schedule(self.holed, "CARROT", True, 10)
        with self.assertRaises(subject.SlotCapacityError):
            subject.executable_can_schedule(self.holed, "CARROT", 1, False)


if __name__ == "__main__":
    unittest.main()
