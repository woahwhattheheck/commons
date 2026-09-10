# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import unittest

import compare_three_arm as compare


def hexdigest(label: str, length: int = 64) -> str:
    value = hashlib.sha256(label.encode("utf-8")).hexdigest()
    return value[:length]


def game(
    *,
    opponent: str,
    seed: int,
    seat: int,
    own: float,
    rival: float,
    action_label: str,
) -> dict:
    scores = [0.0, 0.0]
    scores[seat] = own
    scores[1 - seat] = rival
    return {
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "scores": scores,
        "failure": None,
        "steps": compare.EXPECTED_ACTIONS,
        "episode_steps": compare.EXPECTED_EPISODE_STEPS,
        "daily_bank": [
            {"step": 23, "bank": [0.0, 0.0]},
            {"step": 718, "bank": list(scores)},
        ],
        "actors": [
            {
                "calls": compare.EXPECTED_ACTIONS,
                "exit_code": 0,
                "max_call_seconds": 0.01,
            },
            {
                "calls": compare.EXPECTED_ACTIONS,
                "exit_code": 0,
                "max_call_seconds": 0.01,
            },
        ],
        "bank_snapshot": list(scores),
        "trace_sha256": hexdigest(
            f"trace:{action_label}:{opponent}:{seed}:{seat}"
        ),
        "candidate_action_sha256": hexdigest(
            f"action:{action_label}:{opponent}:{seed}:{seat}"
        ),
        "candidate_action_count": compare.EXPECTED_ACTIONS,
        "opponent": opponent,
    }


def panel(
    *,
    wrapper: str,
    own_delta: float,
    action_label: str,
    invocation_label: str,
) -> dict:
    games = []
    for opponent in compare.expected_opponents():
        for seed in compare.EXPECTED_SEEDS:
            for seat in (0, 1):
                games.append(
                    game(
                        opponent=opponent,
                        seed=seed,
                        seat=seat,
                        own=100.0 + own_delta,
                        rival=90.0,
                        action_label=action_label,
                    )
                )
    return {
        "schema_version": 1,
        "invocation_id": hexdigest(invocation_label, 32),
        "engine_ref": compare.EXPECTED_ENGINE_REF,
        "engine_sha256": compare.EXPECTED_ENGINE_SHA256,
        "loader_sha256": compare.EXPECTED_LOADER_SHA256,
        "evaluator_sha256": compare.EXPECTED_EVALUATOR_SHA256,
        "candidate": {
            "entry": "bound_entry.py",
            "callable": "agent",
            "sha256": wrapper,
        },
        "opponents": compare.expected_opponents(),
        "seeds": list(compare.EXPECTED_SEEDS),
        "agent_rng_seed": compare.EXPECTED_RNG_SEED,
        "python": "3.11 synthetic",
        "platform": "linux",
        "limits": dict(compare.EXPECTED_LIMITS),
        "method": "Official interpreter synthetic contract fixture",
        "progress": {
            "state": "complete",
            "phase": "finalize",
            "planned_games": compare.EXPECTED_GAMES,
            "recorded_games": compare.EXPECTED_GAMES,
            "active_game": None,
        },
        "games": games,
    }


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.arms = {
            "control": {"wrapper_sha256": "1" * 64},
            "strict": {"wrapper_sha256": "2" * 64},
            "repair": {"wrapper_sha256": "3" * 64},
        }

    def fixtures(self, *, strict_delta=10, repair_delta=5):
        return (
            panel(
                wrapper="1" * 64,
                own_delta=0,
                action_label="control",
                invocation_label="control",
            ),
            panel(
                wrapper="2" * 64,
                own_delta=strict_delta,
                action_label="strict",
                invocation_label="strict",
            ),
            panel(
                wrapper="3" * 64,
                own_delta=repair_delta,
                action_label="repair",
                invocation_label="repair",
            ),
        )

    def test_repair_beats_control_without_dominating_strict(self):
        control, strict, repair = self.fixtures()
        result = compare.classify(control, strict, repair, self.arms)
        self.assertEqual(result["verdict"], "REPAIR_BEATS_CONTROL")
        self.assertTrue(result["passes_no_negative_control_screen"])
        self.assertEqual(result["preferred_arm_under_no_negative_guard"], "strict")
        self.assertEqual(result["repair_vs_control"]["mean_own_delta"], 5.0)
        self.assertEqual(result["repair_vs_control"]["cells"], 16)

    def test_repair_dominates_control_and_strict(self):
        control, strict, repair = self.fixtures(strict_delta=3, repair_delta=7)
        result = compare.classify(control, strict, repair, self.arms)
        self.assertEqual(result["verdict"], "REPAIR_DOMINATES_CONTROL_AND_STRICT")
        self.assertEqual(result["preferred_arm_under_no_negative_guard"], "repair")

    def test_equal_mean_but_cellwise_mixed_keeps_strict_preferred(self):
        control, strict, repair = self.fixtures(strict_delta=5, repair_delta=5)
        for index, row in enumerate(repair["games"]):
            seat = row["candidate_seat"]
            own = 106.0 if index < 8 else 104.0
            row["scores"][seat] = own
            row["bank_snapshot"][seat] = own
            row["daily_bank"][-1]["bank"][seat] = own
        result = compare.classify(control, strict, repair, self.arms)
        self.assertEqual(result["verdict"], "REPAIR_BEATS_CONTROL")
        self.assertEqual(result["repair_vs_control"]["mean_own_delta"], 5.0)
        self.assertEqual(result["preferred_arm_under_no_negative_guard"], "strict")
        self.assertGreater(result["repair_vs_strict"]["negative_own_cells"], 0)

    def test_negative_cell_is_mixed_and_fails_gate(self):
        control, strict, repair = self.fixtures(strict_delta=1, repair_delta=3)
        seat = repair["games"][0]["candidate_seat"]
        repair["games"][0]["scores"][seat] = 99.0
        repair["games"][0]["bank_snapshot"][seat] = 99.0
        repair["games"][0]["daily_bank"][-1]["bank"][seat] = 99.0
        result = compare.classify(control, strict, repair, self.arms)
        self.assertEqual(result["verdict"], "REPAIR_MIXED_UPSIDE")
        self.assertFalse(result["passes_no_negative_control_screen"])

    def test_no_action_change_is_not_promotable(self):
        control, strict, repair = self.fixtures(strict_delta=1, repair_delta=5)
        for before, after in zip(control["games"], repair["games"]):
            after["candidate_action_sha256"] = before["candidate_action_sha256"]
        result = compare.classify(control, strict, repair, self.arms)
        self.assertEqual(result["verdict"], "NO_REPAIR_ACTION_CHANGE")
        self.assertFalse(result["passes_no_negative_control_screen"])

    def test_common_runtime_mismatch_is_rejected(self):
        control, strict, repair = self.fixtures()
        repair["platform"] = "different"
        with self.assertRaisesRegex(compare.ClassificationError, "runtime mismatch"):
            compare.classify(control, strict, repair, self.arms)

    def test_duplicate_cell_is_rejected(self):
        control, _strict, _repair = self.fixtures()
        control["games"][1] = copy.deepcopy(control["games"][0])
        with self.assertRaisesRegex(compare.ClassificationError, "duplicate game cell"):
            compare.validate_panel(
                control, arm="control", binding_arm=self.arms["control"]
            )

    def test_bank_mismatch_is_rejected(self):
        control, _strict, _repair = self.fixtures()
        control["games"][0]["bank_snapshot"][0] += 1
        with self.assertRaisesRegex(compare.ClassificationError, "bank snapshot"):
            compare.validate_panel(
                control, arm="control", binding_arm=self.arms["control"]
            )

    def test_boolean_seat_is_rejected(self):
        control, _strict, _repair = self.fixtures()
        control["games"][0]["candidate_seat"] = True
        with self.assertRaisesRegex(compare.ClassificationError, "candidate_seat"):
            compare.validate_panel(
                control, arm="control", binding_arm=self.arms["control"]
            )

    def test_duplicate_invocation_is_rejected(self):
        control, strict, repair = self.fixtures()
        repair["invocation_id"] = strict["invocation_id"]
        with self.assertRaisesRegex(compare.ClassificationError, "not distinct"):
            compare.classify(control, strict, repair, self.arms)

    def test_nonfinite_daily_bank_is_rejected(self):
        control, _strict, _repair = self.fixtures()
        control["games"][0]["daily_bank"][0]["bank"][0] = float("nan")
        with self.assertRaisesRegex(compare.ClassificationError, "not finite"):
            compare.validate_panel(
                control, arm="control", binding_arm=self.arms["control"]
            )

    def test_wrong_seed_grid_is_rejected(self):
        control, _strict, _repair = self.fixtures()
        control["seeds"][0] += 1
        with self.assertRaisesRegex(compare.ClassificationError, "seed grid"):
            compare.validate_panel(
                control, arm="control", binding_arm=self.arms["control"]
            )

    def test_opponent_actor_failure_is_rejected(self):
        control, _strict, _repair = self.fixtures()
        control["games"][0]["actors"][1]["exit_code"] = 1
        with self.assertRaisesRegex(compare.ClassificationError, "actor 1 failed"):
            compare.validate_panel(
                control, arm="control", binding_arm=self.arms["control"]
            )


if __name__ == "__main__":
    unittest.main()
