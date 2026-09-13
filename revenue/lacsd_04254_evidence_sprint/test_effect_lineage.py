from __future__ import annotations

import copy
import unittest

from evidence_sprint import ValidationError, evaluate_candidate, reference_candidate


class EffectLineageTests(unittest.TestCase):
    def test_effect_id_cannot_cross_scenario_or_input_lineage(self):
        candidate = copy.deepcopy(reference_candidate())
        for event in candidate["events"]:
            if event["disposition"] == "ALERT":
                event["effect_id"] = "effect-shared"
        with self.assertRaisesRegex(
            ValidationError,
            "effect_id reused across distinct scenario/input lineage",
        ):
            evaluate_candidate(candidate)

    def test_idempotent_repeat_inside_one_binding_remains_valid(self):
        candidate = copy.deepcopy(reference_candidate())
        base = next(
            event
            for event in candidate["events"]
            if event["scenario_id"] == "duplicate-replay-01"
        )
        repeated = dict(base)
        repeated["event_id"] = "event-duplicate-replay-idempotent-repeat"
        candidate["events"].append(repeated)
        result = evaluate_candidate(candidate)
        self.assertEqual(result["status"], "READY_FOR_BUYER_REVIEW")
        self.assertEqual(result["duplicate_effect_count"], 0)


if __name__ == "__main__":
    unittest.main()
