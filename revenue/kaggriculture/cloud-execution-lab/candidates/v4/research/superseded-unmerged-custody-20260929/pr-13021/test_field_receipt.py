# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

from field_receipt import build_receipt, classify_record, reduce_records


def rec(scores, returned):
    return {
        "step": 123,
        "player": 0,
        "diagnostics": {"status": "applied", "scores": scores},
        "returned_market": returned,
    }


class ReturnedActionGateTests(unittest.TestCase):
    def test_true_reorder_survives_exact_returned_prefix(self):
        record = rec(
            [
                {"original_index": 0, "item": "WHEAT", "requested": 1, "impact": 1},
                {"original_index": 1, "item": "CARROT", "requested": 2, "impact": 10},
            ],
            [["SELL", "CARROT", 2], ["SELL", "WHEAT", 1], ["HIRE"]],
        )
        result = classify_record(record)
        self.assertEqual(result["classification"], "returned_reorder_witness")
        self.assertTrue(result["returned_reorder"])

    def test_downstream_restore_kills_internal_witness(self):
        record = rec(
            [
                {"original_index": 0, "item": "WHEAT", "requested": 1, "impact": 1},
                {"original_index": 1, "item": "CARROT", "requested": 2, "impact": 10},
            ],
            [["SELL", "WHEAT", 1], ["SELL", "CARROT", 2]],
        )
        result = classify_record(record)
        self.assertEqual(result["classification"], "internal_reorder_not_returned")
        self.assertTrue(result["internal_reorder"])
        self.assertFalse(result["returned_reorder"])

    def test_inserted_downstream_row_kills_witness(self):
        record = rec(
            [
                {"original_index": 0, "item": "WHEAT", "requested": 1, "impact": 1},
                {"original_index": 1, "item": "CARROT", "requested": 2, "impact": 10},
            ],
            [["SELL", "MELON", 3], ["SELL", "CARROT", 2], ["SELL", "WHEAT", 1]],
        )
        self.assertEqual(classify_record(record)["classification"], "internal_reorder_not_returned")

    def test_duplicate_signature_is_ambiguous_even_if_positions_look_right(self):
        record = rec(
            [
                {"original_index": 0, "item": "MELON", "requested": 2, "impact": 1},
                {"original_index": 1, "item": "MELON", "requested": 2, "impact": 9},
            ],
            [["SELL", "MELON", 2], ["SELL", "MELON", 2]],
        )
        result = classify_record(record)
        self.assertEqual(result["classification"], "ambiguous_duplicate_sell_signature")
        self.assertFalse(result["internal_reorder"])
        self.assertFalse(result["returned_reorder"])

    def test_extended_sell_row_is_not_exact_identity(self):
        record = rec(
            [
                {"original_index": 0, "item": "WHEAT", "requested": 1, "impact": 1},
                {"original_index": 1, "item": "CARROT", "requested": 2, "impact": 10},
            ],
            [["SELL", "CARROT", 2, "extra"], ["SELL", "WHEAT", 1]],
        )
        self.assertEqual(
            classify_record(record)["classification"],
            "returned_prefix_malformed_or_extended",
        )

    def test_identity_rank_is_not_a_reorder(self):
        record = rec(
            [
                {"original_index": 0, "item": "CARROT", "requested": 2, "impact": 10},
                {"original_index": 1, "item": "WHEAT", "requested": 1, "impact": 1},
            ],
            [["SELL", "CARROT", 2], ["SELL", "WHEAT", 1]],
        )
        result = classify_record(record)
        self.assertEqual(result["classification"], "identity_rank")
        self.assertFalse(result["internal_reorder"])

    def test_noncontiguous_original_indices_fail_closed(self):
        record = rec(
            [
                {"original_index": 0, "item": "WHEAT", "requested": 1, "impact": 1},
                {"original_index": 2, "item": "CARROT", "requested": 2, "impact": 10},
            ],
            [["SELL", "CARROT", 2], ["SELL", "WHEAT", 1]],
        )
        self.assertEqual(classify_record(record)["classification"], "invalid_original_indices")

    def test_bool_quantity_is_rejected(self):
        record = rec(
            [
                {"original_index": 0, "item": "WHEAT", "requested": True, "impact": 1},
                {"original_index": 1, "item": "CARROT", "requested": 2, "impact": 10},
            ],
            [["SELL", "CARROT", 2], ["SELL", "WHEAT", 1]],
        )
        self.assertEqual(classify_record(record)["classification"], "invalid_scores")

    def test_reduce_counts_internal_and_returned_separately(self):
        scores = [
            {"original_index": 0, "item": "WHEAT", "requested": 1, "impact": 1},
            {"original_index": 1, "item": "CARROT", "requested": 2, "impact": 10},
        ]
        records = [
            rec(scores, [["SELL", "CARROT", 2], ["SELL", "WHEAT", 1]]),
            rec(scores, [["SELL", "WHEAT", 1], ["SELL", "CARROT", 2]]),
        ]
        reduced = reduce_records(records)
        self.assertEqual(reduced["applied_callbacks"], 2)
        self.assertEqual(reduced["internal_reorder_callbacks"], 2)
        self.assertEqual(reduced["returned_reorder_callbacks"], 1)
        self.assertEqual(
            reduced["blocked_callback_counts"],
            {"internal_reorder_not_returned": 1},
        )

    def test_v1_false_green_is_overridden_by_v2(self):
        scores = [
            {"original_index": 0, "item": "WHEAT", "requested": 1, "impact": 1},
            {"original_index": 1, "item": "CARROT", "requested": 2, "impact": 10},
        ]
        v1 = {
            "schema": "titan-v4-row-shed-postimage-field/v1",
            "verdict": "NATURAL_REORDER_WITNESS",
            "natural_reorder_callbacks": 1,
            "natural_reorder_witness": True,
            "economics_are_promotion_authority": False,
            "production_activated": False,
            "promotion_authorized": False,
        }
        v2 = build_receipt(v1, [
            rec(scores, [["SELL", "WHEAT", 1], ["SELL", "CARROT", 2]])
        ])
        self.assertEqual(
            v2["verdict"],
            "NATURAL_ENGAGEMENT_NO_RETURNED_REORDER_IN_PANEL",
        )
        self.assertEqual(v2["natural_reorder_callbacks"], 0)
        self.assertFalse(v2["natural_reorder_witness"])
        self.assertEqual(
            v2["returned_action_gate"]["old_unbound_verdict"],
            "NATURAL_REORDER_WITNESS",
        )

    def test_v2_positive_verdict_requires_returned_action_bound_witness(self):
        scores = [
            {"original_index": 0, "item": "WHEAT", "requested": 1, "impact": 1},
            {"original_index": 1, "item": "CARROT", "requested": 2, "impact": 10},
        ]
        v2 = build_receipt({}, [
            rec(scores, [["SELL", "CARROT", 2], ["SELL", "WHEAT", 1]])
        ])
        self.assertEqual(
            v2["verdict"],
            "NATURAL_REORDER_WITNESS_RETURNED_ACTION_BOUND",
        )
        self.assertTrue(v2["natural_reorder_witness"])
        self.assertFalse(v2["promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
