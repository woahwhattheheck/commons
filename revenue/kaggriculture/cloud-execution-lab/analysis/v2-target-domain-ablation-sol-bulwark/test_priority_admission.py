# SPDX-License-Identifier: Apache-2.0
"""Predecessor-discriminating tests for the priority admission gate."""
from __future__ import annotations

import copy
import unittest

import priority_admission as admission


OPPONENTS = ("arlene", "v1")
SEEDS = (
    539131249,
    1834999074,
    2609097301,
    2609097302,
    2609097303,
    2609097304,
    2611092201,
    2611092207,
)


def receipt() -> dict:
    return {
        "schema_version": 1,
        "experiment": admission.EXPERIMENT,
        "source": {
            "scheduler_git_blob_sha1": (
                admission.compare.V2_SCHEDULER_BLOB
            )
        },
        "ablation": {
            "changed_files": ["scheduler.py"],
            "old_occurrences_before": 1,
            "old_occurrences_after": 0,
            "new_occurrences_before": 0,
            "new_occurrences_after": 1,
        },
    }


def report(
    *,
    own_delta: float = 2,
    rival_delta: float = 0,
    changed: bool = True,
) -> dict:
    rows = []
    for opponent in OPPONENTS:
        for seed in SEEDS:
            for seat in (0, 1):
                control_own = 100.0
                control_rival = 90.0
                candidate_own = control_own + own_delta
                candidate_rival = control_rival + rival_delta
                rows.append(
                    {
                        "opponent": opponent,
                        "seed": seed,
                        "seat": seat,
                        "control_own": control_own,
                        "control_rival": control_rival,
                        "ablation_own": candidate_own,
                        "ablation_rival": candidate_rival,
                        "own_delta": own_delta,
                        "rival_delta": rival_delta,
                        "margin_delta": own_delta - rival_delta,
                        "candidate_action_changed": changed,
                    }
                )
    return {
        "schema_version": 2,
        "git_head": "a" * 40,
        "verdict": "UPSIDE_SCREEN",
        "exit_code": 0,
        "rows": rows,
    }


class PriorityAdmissionTests(unittest.TestCase):
    def test_clean_positive_panel_is_admitted(self) -> None:
        result = admission.assess(report(), receipt())
        self.assertEqual(result["verdict"], "ADMIT")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["overall"]["new_losses"], 0)
        self.assertGreater(result["overall"]["mean_margin_delta"], 0)
        self.assertTrue(all(result["gates"].values()))

    def test_new_loss_is_rejected_despite_positive_aggregate(self) -> None:
        candidate = report(own_delta=4)
        first = candidate["rows"][0]
        first["ablation_own"] = 80.0
        first["own_delta"] = -20.0
        first["margin_delta"] = -20.0

        result = admission.assess(candidate, receipt())
        self.assertEqual(result["verdict"], "REJECT")
        self.assertEqual(result["overall"]["new_losses"], 1)
        self.assertFalse(result["gates"]["zero_new_losses"])

    def test_negative_margin_is_rejected_despite_own_cash_gain(self) -> None:
        result = admission.assess(
            report(own_delta=4, rival_delta=7),
            receipt(),
        )
        self.assertEqual(result["verdict"], "REJECT")
        self.assertFalse(result["gates"]["positive_mean_margin"])

    def test_losing_opponent_seat_stratum_is_rejected(self) -> None:
        candidate = report(own_delta=3)
        for row in candidate["rows"]:
            if row["opponent"] == "arlene" and row["seat"] == 0:
                row["ablation_own"] = 99.0
                row["own_delta"] = -1.0
                row["margin_delta"] = -1.0

        result = admission.assess(candidate, receipt())
        self.assertEqual(result["verdict"], "REJECT")
        self.assertFalse(
            result["gates"][
                "all_opponent_seat_strata_nonnegative"
            ]
        )

    def test_no_candidate_action_activation_is_rejected(self) -> None:
        result = admission.assess(
            report(changed=False),
            receipt(),
        )
        self.assertEqual(result["verdict"], "REJECT")
        self.assertFalse(
            result["gates"]["candidate_action_activation"]
        )

    def test_duplicate_cell_fails_closed(self) -> None:
        candidate = report()
        candidate["rows"][-1] = copy.deepcopy(
            candidate["rows"][0]
        )
        with self.assertRaisesRegex(
            admission.AdmissionError,
            "duplicate paired row",
        ):
            admission.assess(candidate, receipt())

    def test_detached_delta_fails_closed(self) -> None:
        candidate = report()
        candidate["rows"][0]["margin_delta"] = 999
        with self.assertRaisesRegex(
            admission.AdmissionError,
            "detached from scores",
        ):
            admission.assess(candidate, receipt())

    def test_wrong_grid_fails_closed(self) -> None:
        candidate = report()
        candidate["rows"][0]["seed"] = 999
        with self.assertRaisesRegex(
            admission.AdmissionError,
            "paired grid mismatch",
        ):
            admission.assess(candidate, receipt())

    def test_wrong_experiment_fails_closed(self) -> None:
        wrong = receipt()
        wrong["experiment"] = "other"
        with self.assertRaisesRegex(
            admission.AdmissionError,
            "experiment mismatch",
        ):
            admission.assess(report(), wrong)


if __name__ == "__main__":
    unittest.main(verbosity=2)
