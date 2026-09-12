#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import base64
import json
import unittest
import zlib

import audit_authored_routes as audit
import market_order_budget as budget


class MarketOrderBudgetTests(unittest.TestCase):
    def test_engine_default_cap(self):
        self.assertEqual(budget.DEFAULT_CAP, 10)
        self.assertEqual(budget._cap(0), 1)
        self.assertEqual(budget._cap("12"), 12)

    def test_below_cap_appends_without_displacing(self):
        action = {"market": [["SELL", "EGG", 1], []]}
        row = budget.analyze_action(action, 10)
        self.assertEqual(row["admission_slot"], 1)
        self.assertFalse(row["structural_overflow"])
        self.assertEqual(row["dropped_nonempty_count"], 0)

    def test_fixed_ten_rows_can_use_existing_hole(self):
        market = [["SELL", "EGG", 1]] * 10
        market[6] = []
        row = budget.analyze_action({"market": market}, 10)
        self.assertEqual(row["admission_slot"], 6)
        self.assertEqual(row["raw_rows"], 10)
        self.assertFalse(row["structural_overflow"])

    def test_full_ten_rows_has_no_admission_slot(self):
        market = [["SELL", "EGG", 1]] * 10
        row = budget.analyze_action({"market": market}, 10)
        self.assertIsNone(row["admission_slot"])
        self.assertEqual(row["executable_active_rows"], 10)

    def test_nonempty_slot_ten_is_dropped(self):
        market = [[] for _ in range(10)] + [["BUY_ANIMAL", "SHEEP", 1]]
        row = budget.analyze_action({"market": market}, 10)
        self.assertTrue(row["structural_overflow"])
        self.assertEqual(row["dropped_nonempty"], [{"slot": 10, "order": ["BUY_ANIMAL", "SHEEP", 1]}])
        self.assertEqual(row["executable_active_rows"], 0)

    def test_adjacent_same_orders_are_not_compacted(self):
        # The engine budget is raw rows, not quantity units. Even identical
        # adjacent rows retain distinct rival-aligned execution positions, so
        # ORDERBUDGET must report rather than silently consolidate them.
        market = [["SELL", "EGG", 1] for _ in range(11)]
        row = budget.analyze_action({"market": market}, 10)
        self.assertEqual(row["raw_rows"], 11)
        self.assertEqual(row["executable_active_rows"], 10)
        self.assertEqual(
            row["dropped_nonempty"],
            [{"slot": 10, "order": ["SELL", "EGG", 1]}],
        )
        self.assertIsNone(row["admission_slot"])

    def test_empty_overflow_is_structural_not_effective(self):
        row = budget.analyze_action({"market": [[] for _ in range(12)]}, 10)
        self.assertTrue(row["structural_overflow"])
        self.assertEqual(row["dropped_nonempty_count"], 0)
        self.assertEqual(row["overflow_rows"], 2)

    def test_scan_distinguishes_headroom_and_overflow(self):
        actions = [
            {"market": []},
            {"market": [["HIRE"]] * 10},
            {"market": [[] for _ in range(10)] + [["SELL", "WOOL", 2]]},
        ]
        report = budget.scan_actions(actions, 10)
        self.assertEqual(report["callbacks"], 3)
        self.assertEqual(report["structural_overflow_callbacks"], 1)
        self.assertEqual(report["dropped_nonempty_callbacks"], 1)
        self.assertEqual(report["dropped_nonempty_rows"], 1)
        self.assertEqual(report["no_admission_slot_callbacks"], 1)

    def test_malformed_market_fails_closed(self):
        with self.assertRaises(TypeError):
            budget.analyze_action({"market": "SELL"})
        with self.assertRaises(TypeError):
            budget.analyze_action({"market": [[1, "EGG", 1]]})

    def test_route_decoder_reconstructs_tails(self):
        payload = {
            "main": "a",
            "full": [{"market": []}, {"market": [["HIRE"]]}],
            "tails": [{"h": "b", "parent": "a", "at": 1, "suffix": [{"market": [["BUY_LAND"]]}]}],
        }
        blob = base64.b64encode(zlib.compress(json.dumps(payload).encode())).decode()
        routes = audit.decode_routes(f"_BLOB = {blob!r}\n")
        self.assertEqual(routes["a"][1]["market"], [["HIRE"]])
        self.assertEqual(routes["b"][1]["market"], [["BUY_LAND"]])

    def test_admission_is_planning_only(self):
        action = {"market": [[], ["SELL", "MILK", 1]]}
        before = json.dumps(action, sort_keys=True)
        self.assertEqual(budget.admission_slot(action), 0)
        self.assertEqual(json.dumps(action, sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
