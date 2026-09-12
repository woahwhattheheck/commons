#!/usr/bin/env python3
from __future__ import annotations

import unittest

import run_predictable_procurement_field as field


class PredictableProcurementFieldTests(unittest.TestCase):
    def pulse(self, row=1, item="WHEAT", qty=3):
        return {"step": 10, "row": row, "item": item, "qty": qty}

    def test_natural_cobuy_alignment(self):
        rows = [[], ["BUY_PRODUCT", "WHEAT", 2]]
        r = field._event_candidates(rows, self.pulse(row=1), 10)
        self.assertTrue(r["natural_cobuy_row"])
        self.assertEqual(r["cobuy_realign_source_rows"], [])

    def test_blank_target_exposes_realign_candidate_without_claiming_authority(self):
        rows = [["BUY_PRODUCT", "WHEAT", 2], []]
        r = field._event_candidates(rows, self.pulse(row=1), 10)
        self.assertFalse(r["natural_cobuy_row"])
        self.assertEqual(r["cobuy_realign_source_rows"], [0])

    def test_occupied_target_blocks_realign_candidate(self):
        rows = [["BUY_PRODUCT", "WHEAT", 2], ["BUY_SEED", "CARROT", 1]]
        r = field._event_candidates(rows, self.pulse(row=1), 10)
        self.assertEqual(r["cobuy_realign_source_rows"], [])

    def test_same_row_sell_with_blank_successor_is_delay_candidate(self):
        rows = [[], ["SELL", "FERTILIZER", 4], []]
        r = field._event_candidates(rows, self.pulse(row=1, item="FERTILIZER"), 10)
        self.assertTrue(r["crosssell_same_row"])
        self.assertTrue(r["crosssell_delay_one_row_candidate"])

    def test_occupied_successor_blocks_delay_candidate(self):
        rows = [[], ["SELL", "WHEAT", 4], ["BUY_SEED", "CARROT", 1]]
        r = field._event_candidates(rows, self.pulse(row=1), 10)
        self.assertTrue(r["crosssell_same_row"])
        self.assertFalse(r["crosssell_delay_one_row_candidate"])

    def test_later_sell_is_recorded_as_already_after(self):
        rows = [[], ["BUY_SEED", "CARROT", 1], ["SELL", "WHEAT", 4]]
        r = field._event_candidates(rows, self.pulse(row=1), 10)
        self.assertEqual(r["crosssell_already_after"], [2])

    def test_raw_cap_excludes_suffix_activity(self):
        rows = [[] for _ in range(10)] + [["SELL", "WHEAT", 9]]
        r = field._event_candidates(rows, self.pulse(row=1), 10)
        self.assertEqual(r["own_same_item_sell_rows"], [])

    def test_bool_quantity_does_not_exactly_match_predictor(self):
        self.assertFalse(field._row_is(["BUY_PRODUCT", "WHEAT", True], "BUY_PRODUCT", "WHEAT", 1))
        self.assertTrue(field._row_is(["BUY_PRODUCT", "WHEAT", 1], "BUY_PRODUCT", "WHEAT", 1))


if __name__ == "__main__":
    unittest.main()
