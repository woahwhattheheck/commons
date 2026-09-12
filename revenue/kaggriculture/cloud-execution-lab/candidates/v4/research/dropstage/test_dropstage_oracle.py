#!/usr/bin/env python3
from __future__ import annotations

import unittest
import dropstage_oracle as d


class DropStageTests(unittest.TestCase):
    def test_constructed_exact_semantic_witness(self):
        receipt = d.proof_receipt(3, 1, 3)
        self.assertEqual(receipt["drop"]["deposited_before_market"], 1)
        self.assertEqual(receipt["drop"]["destroyed_before_market"], 2)
        self.assertEqual(receipt["place"]["deposited_before_market"], 1)
        self.assertEqual(receipt["place"]["carried_into_market"], 2)
        self.assertEqual(receipt["place"]["returned_at_eod"], 2)
        self.assertEqual(receipt["place"]["destroyed_at_eod"], 0)
        self.assertEqual(receipt["saved_units"], 2)
        self.assertEqual(receipt["market_start_shed_delta"], 0)

    def test_admits_only_full_non_crowding_rescue(self):
        self.assertEqual(d.admit_dropstage(
            carried_inputs={"CORN": 3}, shed_free_before_units=1,
            eod_room_after_market_lower_bound=4, other_eod_carry_units=2,
            is_final_callback_of_day=True, place_supported=True),
            ["PLACE", "CORN", 3])

    def test_rejects_partial_future_room(self):
        self.assertIsNone(d.admit_dropstage(
            carried_inputs={"CORN": 3}, shed_free_before_units=1,
            eod_room_after_market_lower_bound=1, other_eod_carry_units=0,
            is_final_callback_of_day=True, place_supported=True))

    def test_rejects_crowding_other_eod_carry(self):
        self.assertIsNone(d.admit_dropstage(
            carried_inputs={"CORN": 3}, shed_free_before_units=1,
            eod_room_after_market_lower_bound=3, other_eod_carry_units=2,
            is_final_callback_of_day=True, place_supported=True))

    def test_rejects_multi_item_carry(self):
        self.assertIsNone(d.admit_dropstage(
            carried_inputs={"CORN": 3, "MILK": 1}, shed_free_before_units=1,
            eod_room_after_market_lower_bound=10, other_eod_carry_units=0,
            is_final_callback_of_day=True, place_supported=True))

    def test_rejects_when_drop_is_lossless(self):
        self.assertIsNone(d.admit_dropstage(
            carried_inputs={"CORN": 3}, shed_free_before_units=3,
            eod_room_after_market_lower_bound=10, other_eod_carry_units=0,
            is_final_callback_of_day=True, place_supported=True))

    def test_rejects_non_eod(self):
        self.assertIsNone(d.admit_dropstage(
            carried_inputs={"CORN": 3}, shed_free_before_units=1,
            eod_room_after_market_lower_bound=10, other_eod_carry_units=0,
            is_final_callback_of_day=False, place_supported=True))

    def test_rejects_unproved_place_support(self):
        self.assertIsNone(d.admit_dropstage(
            carried_inputs={"CORN": 3}, shed_free_before_units=1,
            eod_room_after_market_lower_bound=10, other_eod_carry_units=0,
            is_final_callback_of_day=True, place_supported=False))

    def test_malformed_inputs_fail_closed(self):
        bad = ({"CORN": -1}, {"": 2}, {"CORN": True})
        for carried in bad:
            self.assertIsNone(d.admit_dropstage(
                carried_inputs=carried, shed_free_before_units=1,
                eod_room_after_market_lower_bound=10, other_eod_carry_units=0,
                is_final_callback_of_day=True, place_supported=True))
        self.assertIsNone(d.admit_dropstage(
            carried_inputs={"CORN": 3}, shed_free_before_units=True,
            eod_room_after_market_lower_bound=10, other_eod_carry_units=0,
            is_final_callback_of_day=True, place_supported=True))


if __name__ == "__main__":
    unittest.main()
