# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

import economic_admission as admission
import test_compare_three_arm as fixtures


def set_terminal(row: dict, *, own: float, rival: float) -> None:
    seat = row["candidate_seat"]
    scores = [0.0, 0.0]
    scores[seat] = own
    scores[1 - seat] = rival
    row["scores"] = scores
    row["bank_snapshot"] = list(scores)
    row["daily_bank"][-1]["bank"] = list(scores)


def copy_evidence(source: dict, target: dict) -> None:
    for field in (
        "scores",
        "bank_snapshot",
        "daily_bank",
        "trace_sha256",
        "candidate_action_sha256",
    ):
        target[field] = copy.deepcopy(source[field])


class EconomicAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.arms = {
            "control": {"wrapper_sha256": "1" * 64},
            "strict": {"wrapper_sha256": "2" * 64},
            "repair": {"wrapper_sha256": "3" * 64},
        }

    def panels(self, *, strict_delta: float, repair_delta: float):
        return (
            fixtures.panel(
                wrapper="1" * 64,
                own_delta=0,
                action_label="control",
                invocation_label="control-economic",
            ),
            fixtures.panel(
                wrapper="2" * 64,
                own_delta=strict_delta,
                action_label="strict",
                invocation_label="strict-economic",
            ),
            fixtures.panel(
                wrapper="3" * 64,
                own_delta=repair_delta,
                action_label="repair",
                invocation_label="repair-economic",
            ),
        )

    def test_complete_positive_panel_admits_repair_but_keeps_better_strict(self):
        control, strict, repair = self.panels(strict_delta=10, repair_delta=5)
        result = admission.classify(control, strict, repair, self.arms)
        self.assertEqual(result["verdict"], "REPAIR_BEATS_CONTROL")
        self.assertTrue(result["passes_economic_admission_gate"])
        self.assertEqual(
            result["preferred_arm_under_economic_admission_gate"], "strict"
        )
        rc = result["repair_vs_control"]
        self.assertEqual(rc["positive_opponent_seed_blocks"], 8)
        self.assertEqual(rc["opponent_seed_sign_tail"], 1 / 256)

    def test_repair_requires_independent_gate_to_displace_strict(self):
        control, strict, repair = self.panels(strict_delta=3, repair_delta=7)
        result = admission.classify(control, strict, repair, self.arms)
        self.assertEqual(result["verdict"], "REPAIR_DOMINATES_CONTROL_AND_STRICT")
        self.assertEqual(
            result["preferred_arm_under_economic_admission_gate"], "repair"
        )

    def test_sixteen_win_to_loss_flips_are_rejected(self):
        control, strict, repair = self.panels(strict_delta=0, repair_delta=1)
        for row in repair["games"]:
            set_terminal(row, own=101.0, rival=120.0)
        result = admission.classify(control, strict, repair, self.arms)
        self.assertFalse(result["passes_economic_admission_gate"])
        self.assertEqual(result["repair_vs_control"]["new_losses"], 16)
        self.assertEqual(result["repair_vs_control"]["lost_wins"], 16)
        self.assertEqual(result["repair_vs_control"]["mean_margin_delta"], -29.0)

    def test_repair_identical_to_strict_cannot_displace_strict(self):
        control, strict, repair = self.panels(strict_delta=5, repair_delta=5)
        for source, target in zip(strict["games"], repair["games"]):
            copy_evidence(source, target)
        result = admission.classify(control, strict, repair, self.arms)
        self.assertEqual(
            result["preferred_arm_under_economic_admission_gate"], "strict"
        )
        self.assertEqual(result["repair_vs_strict"]["changed_action_cells"], 0)
        self.assertFalse(
            result["repair_vs_strict"]["passes_economic_admission_gate"]
        )

    def test_one_activated_cell_cannot_launder_fifteen_inert_cells(self):
        control, strict, repair = self.panels(strict_delta=2, repair_delta=1)
        for source, target in zip(control["games"][1:], repair["games"][1:]):
            copy_evidence(source, target)
        result = admission.classify(control, strict, repair, self.arms)
        self.assertEqual(
            result["verdict"], "REPAIR_INSUFFICIENT_CLUSTERED_SUPPORT"
        )
        rc = result["repair_vs_control"]
        self.assertEqual(rc["realized_action_cells"], 1)
        self.assertEqual(rc["positive_opponent_seed_blocks"], 1)
        self.assertEqual(rc["opponent_seed_sign_tail"], 0.5)

    def test_negative_opponent_seat_margin_is_rejected(self):
        control, strict, repair = self.panels(strict_delta=0, repair_delta=1)
        for row in repair["games"]:
            rival = 130.0 if (
                row["opponent"] == "arlene" and row["candidate_seat"] == 0
            ) else 80.0
            set_terminal(row, own=101.0, rival=rival)
        result = admission.classify(control, strict, repair, self.arms)
        self.assertFalse(result["passes_economic_admission_gate"])
        self.assertEqual(
            result["repair_vs_control"]["subgroup_mean_margin_delta"][
                "arlene/seat-0"
            ],
            -39.0,
        )

    def test_action_identical_trace_or_terminal_drift_is_invalid(self):
        control, strict, repair = self.panels(strict_delta=1, repair_delta=5)
        for source, target in zip(control["games"], repair["games"]):
            target["candidate_action_sha256"] = source[
                "candidate_action_sha256"
            ]
        with self.assertRaisesRegex(admission.AdmissionError, "action-identical"):
            admission.classify(control, strict, repair, self.arms)

    def test_trace_identical_terminal_drift_is_invalid(self):
        control, strict, repair = self.panels(strict_delta=1, repair_delta=5)
        for source, target in zip(control["games"], repair["games"]):
            target["trace_sha256"] = source["trace_sha256"]
        with self.assertRaisesRegex(admission.AdmissionError, "trace-identical"):
            admission.classify(control, strict, repair, self.arms)


if __name__ == "__main__":
    unittest.main()
