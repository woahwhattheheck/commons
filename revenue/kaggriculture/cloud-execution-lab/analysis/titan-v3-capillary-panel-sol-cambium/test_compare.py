# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import unittest

import compare


CONTROL_SHA = "1" * 64
CANDIDATE_SHA = "2" * 64
EVALUATOR_SOURCE_SHA = "3" * 64
PATCHED_SHA = "4" * 64
LOADER_SHA = "5" * 64


def audit_fixture():
    return {
        "schema_version": 1,
        "operation": compare.OPERATION,
        "git_head": "a" * 40,
        "archive": {"sha256": "6" * 64},
        "control": {"sha256": CONTROL_SHA},
        "candidate": {"sha256": CANDIDATE_SHA},
        "evaluator_source": {
            "git_blob_sha1": "b" * 40,
            "sha256": EVALUATOR_SOURCE_SHA,
            "bytes": 123,
        },
        "loader": {"sha256": LOADER_SHA},
        "engine": {
            name: {"sha256": value}
            for name, value in {
                "kaggriculture.py": "7" * 64,
                "kaggriculture.json": "8" * 64,
                "utils.py": "9" * 64,
            }.items()
        },
        "opponents": {
            "arlene": {"sha256": "a" * 64},
            "v1": {"sha256": "b" * 64},
        },
    }


def evaluator_receipt_fixture():
    return {
        "schema_version": 1,
        "operation": compare.OPERATION,
        "source": {
            "git_blob_sha1": "b" * 40,
            "sha256": EVALUATOR_SOURCE_SHA,
            "bytes": 123,
        },
        "patched": {
            "sha256": PATCHED_SHA,
            "capture_phase": "after both returned actions, before interpreter",
            "candidate_action_field": "candidate_action_sha256",
            "candidate_action_count_field": "candidate_action_count",
            "patches": [
                {
                    "old_occurrences_before": 1,
                    "old_occurrences_after": 0,
                    "new_occurrences_after": 1,
                }
                for _ in range(3)
            ],
        },
    }


def report_fixture(entry_sha: str, *, own_delta: float, changed: bool):
    audit = audit_fixture()
    games = []
    for opponent in compare.EXPECTED_OPPONENTS:
        for seed in compare.EXPECTED_SEEDS:
            for seat in (0, 1):
                scores = [100.0, 100.0]
                scores[seat] += own_delta
                token = (
                    f"{opponent}:{seed}:{seat}:"
                    f"{'candidate' if changed else 'control'}"
                ).encode()
                games.append({
                    "opponent": opponent,
                    "seed": seed,
                    "candidate_seat": seat,
                    "status": "complete",
                    "failure": None,
                    "steps": compare.EXPECTED_STEPS,
                    "episode_steps": compare.EXPECTED_EPISODE_STEPS,
                    "scores": scores,
                    "bank_snapshot": list(scores),
                    "candidate_action_count": compare.EXPECTED_STEPS,
                    "candidate_action_sha256": hashlib.sha256(token).hexdigest(),
                    "trace_sha256": hashlib.sha256(b"trace:" + token).hexdigest(),
                    "actors": [
                        {"calls": compare.EXPECTED_STEPS},
                        {"calls": compare.EXPECTED_STEPS},
                    ],
                })
    return {
        "schema_version": 1,
        "engine_ref": compare.EXPECTED_ENGINE_REF,
        "engine_sha256": {
            name: row["sha256"] for name, row in audit["engine"].items()
        },
        "loader_sha256": LOADER_SHA,
        "evaluator_sha256": PATCHED_SHA,
        "candidate": {
            "entry": "candidate.py",
            "callable": "agent",
            "sha256": entry_sha,
        },
        "opponents": {
            "arlene": {
                "entry": "arlene.py",
                "callable": "agent",
                "sha256": "a" * 64,
            },
            "v1": {
                "entry": "candidate.py",
                "callable": "agent",
                "sha256": "b" * 64,
            },
        },
        "seeds": list(compare.EXPECTED_SEEDS),
        "agent_rng_seed": compare.EXPECTED_AGENT_RNG_SEED,
        "limits": {
            "action_rpc_seconds": 1.0,
            "startup_seconds": 15.0,
            "game_seconds_between_steps": 180.0,
            "remaining_overage_time": 0,
        },
        "progress": {
            "state": "complete",
            "phase": "finalize",
            "planned_games": compare.EXPECTED_GAMES_PER_ARM,
            "recorded_games": compare.EXPECTED_GAMES_PER_ARM,
            "active_game": None,
        },
        "games": games,
    }


def indexed(report):
    return {
        (game["opponent"], game["seed"], game["candidate_seat"]): game
        for game in report["games"]
    }


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self.audit = audit_fixture()
        self.receipt = evaluator_receipt_fixture()
        self.control = report_fixture(
            CONTROL_SHA, own_delta=0.0, changed=False
        )

    def classify(self, candidate):
        return compare.classify(
            self.control, candidate, self.audit, self.receipt
        )

    def test_positive_action_bound_panel_advances(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=5.0, changed=True
        )
        result = self.classify(candidate)
        self.assertTrue(result["advance"])
        self.assertEqual(result["metrics"]["official_games"], 32)
        self.assertEqual(result["metrics"]["action_changed_cells"], 16)
        self.assertEqual(result["metrics"]["trace_changed_cells"], 16)
        self.assertEqual(
            result["metrics"]["score_changed_action_bound_cells"], 16
        )
        self.assertEqual(result["metrics"]["mean_own_cash_delta"], 5.0)
        self.assertEqual(result["metrics"]["mean_margin_delta"], 5.0)

    def test_zero_activation_exact_identity_rejects(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=0.0, changed=False
        )
        result = self.classify(candidate)
        self.assertFalse(result["advance"])
        self.assertFalse(result["criteria"]["candidate_actions_changed"])
        self.assertEqual(
            result["metrics"]["action_unchanged_exact_identity_cells"], 16
        )

    def test_negative_own_cash_stratum_rejects(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=10.0, changed=True
        )
        for game in candidate["games"]:
            if game["opponent"] == "arlene" and game["candidate_seat"] == 0:
                game["scores"][0] -= 11.0
                game["bank_snapshot"][0] -= 11.0
        result = self.classify(candidate)
        self.assertGreater(result["metrics"]["mean_own_cash_delta"], 0)
        self.assertFalse(
            result["criteria"][
                "all_opponent_seat_own_cash_strata_nonnegative"
            ]
        )
        self.assertFalse(result["advance"])

    def test_head_to_head_margin_regression_rejects(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=1.0, changed=True
        )
        for game in candidate["games"]:
            rival_seat = 1 - game["candidate_seat"]
            game["scores"][rival_seat] += 900.0
            game["bank_snapshot"][rival_seat] += 900.0
        result = self.classify(candidate)
        self.assertTrue(result["criteria"]["global_mean_own_cash_positive"])
        self.assertTrue(
            result["criteria"][
                "all_opponent_seat_own_cash_strata_nonnegative"
            ]
        )
        self.assertEqual(result["metrics"]["mean_margin_delta"], -899.0)
        self.assertFalse(
            result["criteria"]["global_mean_margin_nonnegative"]
        )
        self.assertFalse(
            result["criteria"][
                "all_opponent_seat_margin_strata_nonnegative"
            ]
        )
        self.assertFalse(result["advance"])

    def test_action_identical_cash_divergence_fails_closed(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=0.0, changed=False
        )
        game = candidate["games"][0]
        seat = game["candidate_seat"]
        game["scores"][seat] += 1.0
        game["bank_snapshot"][seat] += 1.0
        game["trace_sha256"] = "c" * 64
        with self.assertRaisesRegex(
            compare.CompareError, "action-identical causal divergence"
        ):
            self.classify(candidate)

    def test_mixed_cell_activation_cannot_launder_cash_gain(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=0.0, changed=False
        )
        rows = indexed(candidate)
        control_rows = indexed(self.control)
        keys = sorted(rows)

        harmless_activation = rows[keys[0]]
        harmless_activation["candidate_action_sha256"] = "d" * 64
        harmless_activation["trace_sha256"] = "e" * 64

        laundered_gain = rows[keys[1]]
        seat = laundered_gain["candidate_seat"]
        laundered_gain["scores"][seat] += 16.0
        laundered_gain["bank_snapshot"][seat] += 16.0
        self.assertEqual(
            laundered_gain["candidate_action_sha256"],
            control_rows[keys[1]]["candidate_action_sha256"],
        )
        laundered_gain["trace_sha256"] = "f" * 64

        with self.assertRaisesRegex(
            compare.CompareError, "action-identical causal divergence"
        ):
            self.classify(candidate)

    def test_changed_action_without_changed_trace_fails_closed(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=5.0, changed=True
        )
        candidate_rows = indexed(candidate)
        control_rows = indexed(self.control)
        key = sorted(candidate_rows)[0]
        candidate_rows[key]["trace_sha256"] = control_rows[key]["trace_sha256"]
        with self.assertRaisesRegex(
            compare.CompareError, "candidate-action/trace identity mismatch"
        ):
            self.classify(candidate)

    def test_incomplete_game_fails_closed(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=5.0, changed=True
        )
        candidate["games"][0]["status"] = "failed"
        candidate["games"][0]["failure"] = {"kind": "timeout"}
        with self.assertRaisesRegex(compare.CompareError, "incomplete cell"):
            self.classify(candidate)

    def test_score_bank_mismatch_fails_closed(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=5.0, changed=True
        )
        candidate["games"][0]["bank_snapshot"][0] += 1
        with self.assertRaisesRegex(compare.CompareError, "score/bank mismatch"):
            self.classify(candidate)

    def test_evaluator_patch_cardinality_fails_closed(self):
        receipt = copy.deepcopy(self.receipt)
        receipt["patched"]["patches"][1]["old_occurrences_after"] = 1
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=5.0, changed=True
        )
        with self.assertRaisesRegex(compare.CompareError, "cardinality drift"):
            compare.classify(self.control, candidate, self.audit, receipt)

    def test_nonfinal_progress_phase_fails_closed(self):
        candidate = report_fixture(
            CANDIDATE_SHA, own_delta=5.0, changed=True
        )
        candidate["progress"]["phase"] = "games"
        with self.assertRaisesRegex(
            compare.CompareError, "did not finish finalization"
        ):
            self.classify(candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
