# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

import engagement_gate as gate


class RuntimePrefixEngagementGateTests(unittest.TestCase):
    def test_suffix_only_seed_is_wrapper_input_candidate(self):
        action = {"market": [["PASS"]] * 10 + [["BUY_SEED", "WHEAT", 1]]}
        report = gate.classify_wrapper_input("seed", action, {})
        self.assertTrue(report["candidate"])
        self.assertTrue(report["gate_delta"])
        self.assertEqual(report["surface"], gate.WRAPPER_INPUT_SURFACE)
        self.assertEqual(report["cap"], 10)
        self.assertFalse(report["authorizes_global_cold"])

    def test_seed_scope_candidate_is_stage_specific(self):
        action = {"market": [["BUY_SEED", "WHEAT", 1]] + [[]] * 9 + [["BUY_LAND", 0, 0]]}
        seed = gate.classify_wrapper_input("seed", action, {})
        hire = gate.classify_wrapper_input("redundant_hire", action, {})
        self.assertTrue(seed["candidate"])
        self.assertTrue(seed["scope_candidate"])
        self.assertFalse(hire["candidate"])

    def test_suffix_only_fertilizer_is_operating_stock_candidate(self):
        action = {"market": [[]] * 10 + [["SELL", "FERTILIZER", 1]]}
        report = gate.classify_wrapper_input("operating_stock", action, {})
        self.assertTrue(report["candidate"])
        self.assertTrue(report["gate_delta"])

    def test_suffix_only_hire_is_redundant_hire_candidate(self):
        action = {"market": [[]] * 10 + [["HIRE", 1, 2]]}
        report = gate.classify_wrapper_input("redundant_hire", action, {})
        self.assertTrue(report["candidate"])
        self.assertTrue(report["gate_delta"])
        self.assertFalse(report["scope_candidate"])

    def test_final_action_positive_is_steering_only(self):
        action = {"market": [[]] * 10 + [["HIRE", 1, 2]]}
        report = gate.classify_final_action_hint(action, {})
        self.assertTrue(report["candidate"])
        self.assertEqual(report["verdict"], "POSSIBLE_ENGAGEMENT")
        self.assertEqual(report["surface"], gate.FINAL_ACTION_SURFACE)
        self.assertFalse(report["authorizes_global_cold"])
        self.assertTrue(report["stages"])
        self.assertTrue(all(row["surface"] == gate.FINAL_ACTION_SURFACE for row in report["stages"]))
        self.assertTrue(all(row["authorizes_global_cold"] is False for row in report["stages"]))

    def test_zero_final_action_scan_is_inconclusive_not_cold(self):
        hints = [
            gate.classify_final_action_hint({"market": [["PASS"]]}, {}),
            gate.classify_final_action_hint({"market": []}, {}),
        ]
        result = gate.final_action_census(hints)
        self.assertEqual(result["candidate_callbacks"], 0)
        self.assertEqual(result["verdict"], "INCONCLUSIVE_NO_FINAL_ACTION_WITNESS")
        self.assertFalse(result["authorizes_global_cold"])

    def test_configured_cap_receipt_is_not_truncated_to_market_length(self):
        report = gate.classify_wrapper_input("seed", {"market": [["PASS"]]}, {})
        self.assertEqual(report["cap"], 10)
        report = gate.classify_wrapper_input("seed", {"market": [["PASS"], ["HIRE", 1, 2]]}, {"maxMarketOrdersPerTurn": 0})
        self.assertEqual(report["cap"], 1)

    def test_unknown_stage_rejects(self):
        with self.assertRaises(ValueError):
            gate.classify_wrapper_input("final", {"market": []}, {})

    def test_malformed_market_fails_closed_without_cold_authority(self):
        report = gate.classify_wrapper_input("seed", {"market": "bad"}, {})
        self.assertFalse(report["candidate"])
        self.assertEqual(report["reason"], "market_not_list")
        self.assertFalse(report["authorizes_global_cold"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
