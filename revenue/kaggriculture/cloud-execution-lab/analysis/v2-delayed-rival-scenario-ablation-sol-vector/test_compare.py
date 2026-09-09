# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

import compare


def game(opponent: str, seed: int, seat: int, own: float, rival: float, trace: str):
    scores = [own, rival] if seat == 0 else [rival, own]
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "failure": None,
        "steps": 719,
        "episode_steps": 720,
        "scores": scores,
        "trace_sha256": trace,
        "daily_bank": [
            {"step": 23, "bank": [10.0, 10.0]},
            {"step": 718, "bank": list(scores)},
        ],
    }


def report(*, own_shift: float = 0.0, trace: str = "0" * 64):
    games = []
    for opponent in ("arlene", "v1"):
        for seat in (0, 1):
            games.append(
                game(
                    opponent,
                    7,
                    seat,
                    100.0 + own_shift,
                    90.0,
                    trace,
                )
            )
    return {
        "schema_version": 1,
        "engine_ref": compare.ENGINE_REF,
        "engine_sha256": {"kaggriculture.py": "engine"},
        "loader_sha256": "loader",
        "evaluator_sha256": "evaluator",
        "candidate": {
            "entry": "candidate.py",
            "callable": "agent",
            "sha256": compare.V2_ENTRY_SHA256,
        },
        "opponents": {
            "arlene": {"entry": "arlene.py", "sha256": "a"},
            "v1": {"entry": "candidate.py", "sha256": "b"},
        },
        "seeds": [7],
        "agent_rng_seed": 11,
        "limits": {"action_rpc_seconds": 1.0},
        "method": "paired",
        "python": "3.11",
        "games": games,
    }


def receipt():
    return {
        "schema_version": 1,
        "operation": compare.OPERATION,
        "source": {
            "scheduler_git_blob_sha1": compare.V2_SCHEDULER_BLOB,
            "scheduler_sha256": "3" * 64,
            "closure_sha256": "1" * 64,
        },
        "ablation": {
            "factor": "delayed_rival_timing_stress_scenarios",
            "changed_files": ["scheduler.py"],
            "scheduler_git_blob_sha1": "f" * 40,
            "scheduler_sha256": "4" * 64,
            "closure_sha256": "2" * 64,
            "removed_scenarios": list(compare.REMOVED_SCENARIOS),
            "retained_scenarios": list(compare.RETAINED_SCENARIOS),
            "retained_invariants": {
                name: True for name in compare.REQUIRED_INVARIANTS
            },
            "old_occurrences_before": 1,
            "old_occurrences_after": 0,
            "new_occurrences_before": 0,
            "new_occurrences_after": 1,
        },
    }


class CompareTests(unittest.TestCase):
    def test_broad_own_cash_upside_is_screened_in(self):
        value = compare.compare(
            report(),
            report(own_shift=5.0, trace="1" * 64),
            receipt(),
            git_head="abc",
        )
        self.assertEqual(value["verdict"], "UPSIDE_SCREEN")
        self.assertTrue(value["advance_candidate"])
        self.assertEqual(value["overall"]["changed_cells"], 4)
        self.assertEqual(value["overall"]["mean_own_delta"], 5.0)

    def test_identical_actions_are_no_signal(self):
        control = report()
        value = compare.compare(
            control, copy.deepcopy(control), receipt(), git_head="abc"
        )
        self.assertEqual(value["verdict"], "NO_ACTION_SIGNAL")
        self.assertFalse(value["advance_candidate"])

    def test_changed_actions_without_score_change_are_not_upside(self):
        value = compare.compare(
            report(), report(trace="1" * 64), receipt(), git_head="abc"
        )
        self.assertEqual(value["verdict"], "ACTION_NO_SCORE_SIGNAL")

    def test_negative_mean_own_cash_is_regression(self):
        value = compare.compare(
            report(),
            report(own_shift=-5.0, trace="1" * 64),
            receipt(),
            git_head="abc",
        )
        self.assertEqual(value["verdict"], "REGRESSION")
        self.assertFalse(value["advance_candidate"])

    def test_provenance_drift_fails_closed(self):
        candidate = report(own_shift=5.0, trace="1" * 64)
        candidate["evaluator_sha256"] = "different"
        with self.assertRaisesRegex(compare.CompareError, "provenance"):
            compare.compare(report(), candidate, receipt(), git_head="abc")

    def test_missing_cell_fails_closed(self):
        candidate = report(own_shift=5.0, trace="1" * 64)
        candidate["games"].pop()
        with self.assertRaisesRegex(compare.CompareError, "grid mismatch"):
            compare.compare(report(), candidate, receipt(), git_head="abc")

    def test_equal_closure_identities_fail_closed(self):
        bad = receipt()
        bad["ablation"]["closure_sha256"] = bad["source"]["closure_sha256"]
        with self.assertRaisesRegex(compare.CompareError, "equal"):
            compare.compare(report(), report(), bad, git_head="abc")

    def test_wrong_removed_scenario_fails_closed(self):
        bad = receipt()
        bad["ablation"]["removed_scenarios"][0] = "invented"
        with self.assertRaisesRegex(compare.CompareError, "removed scenario"):
            compare.compare(report(), report(), bad, git_head="abc")

    def test_false_retained_invariant_fails_closed(self):
        bad = receipt()
        bad["ablation"]["retained_invariants"][
            "v2_full_continuation_value"
        ] = False
        with self.assertRaisesRegex(compare.CompareError, "not certified"):
            compare.compare(report(), report(), bad, git_head="abc")


if __name__ == "__main__":
    unittest.main()
