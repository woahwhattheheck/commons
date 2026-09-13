from __future__ import annotations

import copy
import unittest

from evidence_sprint import evaluate_candidate, reference_candidate


class GlobalWorkIntentTests(unittest.TestCase):
    def test_reference_candidate_has_no_cross_scenario_effect_collision(self):
        result = evaluate_candidate(reference_candidate())
        self.assertEqual("READY_FOR_BUYER_REVIEW", result["status"])
        self.assertEqual(0, result["cross_scenario_effect_collision_count"])
        self.assertEqual([], result["cross_scenario_effect_ids"])
        self.assertTrue(result["gates"]["duplicate_effect_count_0"])

    def test_one_shared_effect_id_cannot_satisfy_distinct_actionable_scenarios(self):
        candidate = copy.deepcopy(reference_candidate())
        for event in candidate["events"]:
            if event["disposition"] == "ALERT":
                event["effect_id"] = "shared-work-intent-across-scenarios"

        result = evaluate_candidate(candidate)

        # This is the exact landed bypass shape: every individual scenario still has
        # only one local effect, so the old per-scenario metric remains zero.
        self.assertEqual(0, result["duplicate_effect_count"])
        self.assertEqual(1, result["cross_scenario_effect_collision_count"])
        self.assertEqual(
            ["shared-work-intent-across-scenarios"],
            result["cross_scenario_effect_ids"],
        )
        self.assertEqual("HOLD", result["status"])
        self.assertFalse(result["gates"]["duplicate_effect_count_0"])

        exactly_once = next(
            row
            for row in result["claims"]
            if row["claim_id"] == "synthetic.exactly-once-work-intent"
        )
        self.assertFalse(exactly_once["passed"])
        self.assertEqual(0, exactly_once["evidence"]["duplicate_effect_count"])
        self.assertEqual(
            1,
            exactly_once["evidence"]["cross_scenario_effect_collision_count"],
        )

    def test_retry_may_reuse_effect_id_within_same_scenario(self):
        candidate = copy.deepcopy(reference_candidate())
        base = next(
            event
            for event in candidate["events"]
            if event["scenario_id"] == "duplicate-replay-01"
        )
        retry = dict(base)
        retry["event_id"] = "event-duplicate-replay-same-intent-global-test"
        retry["observed_at_s"] = 481
        candidate["events"].append(retry)

        result = evaluate_candidate(candidate)
        self.assertEqual("READY_FOR_BUYER_REVIEW", result["status"])
        self.assertEqual(0, result["duplicate_effect_count"])
        self.assertEqual(0, result["cross_scenario_effect_collision_count"])
        self.assertTrue(result["gates"]["duplicate_effect_count_0"])


if __name__ == "__main__":
    unittest.main()
