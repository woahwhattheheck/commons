# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from certified_report_v3 import AuthenticatedReportError, validate_report_provenance

DONOR_HEAD = "cbfff2bec813e2c2609ce9c5819b74669e98c566"
DONOR_BLOB = "89a3325eb541ae0e8a81e1e0a426292820f10d98"


def expected():
    return {
        "schema_version": 1,
        "engine_ref": "engine-ref",
        "engine_sha256": {"engine.py": "e" * 64},
        "loader_sha256": "l" * 64,
        "evaluator_sha256": "v" * 64,
        "candidate": {"entry": "candidate.py", "callable": "agent", "sha256": "c" * 64},
        "opponents": {"arlene": {"entry": "arlene.py", "callable": "agent", "sha256": "o" * 64}},
        "seeds": [11],
        "agent_rng_seed": 17,
        "limits": {
            "action_rpc_seconds": 1.0,
            "startup_seconds": 15.0,
            "game_seconds_between_steps": 180.0,
            "remaining_overage_time": 0,
        },
        "require_recheck": True,
    }


def diagnostics(*, steps=(), handoff=None):
    return {
        "source_seat": 0,
        "activation_steps": list(steps),
        "activation_count": len(steps),
        "certificate_checks": len(steps),
        "certificate_matches": len(steps),
        "handoff_step": handoff,
        "handoff_reason": None if handoff is None else "test",
        "certificate_donor_head": DONOR_HEAD,
        "certificate_donor_blob": DONOR_BLOB,
    }


def game(seat, *, steps=10, diag=None):
    actors = [{}, {}]
    actors[seat]["agent_diagnostics"] = diag if diag is not None else diagnostics()
    return {
        "opponent": "arlene",
        "seed": 11,
        "candidate_seat": seat,
        "status": "complete",
        "failure": None,
        "scores": [100, 90],
        "trace_sha256": ("a" if seat == 0 else "b") * 64,
        "steps": steps,
        "episode_steps": 12,
        "actors": actors,
    }


def report():
    exp = expected()
    value = {key: copy.deepcopy(exp[key]) for key in (
        "schema_version", "engine_ref", "engine_sha256", "loader_sha256",
        "evaluator_sha256", "candidate", "opponents", "seeds", "agent_rng_seed", "limits",
    )}
    value.update({
        "invocation_id": "0123456789abcdef0123456789abcdef",
        "progress": {"state": "complete", "planned_games": 2, "recorded_games": 2, "active_game": None},
        "reproducibility": {"checked": True, "same_trace_and_scores": True},
        "games": [game(0), game(1)],
    })
    return value


class AuthenticatedReportV3Tests(unittest.TestCase):
    def test_valid_exact_bank_passes(self):
        result = validate_report_provenance(report(), expected(), label="certified", source_seat=0)
        self.assertEqual(result["cells"], 2)

    def test_games_only_report_fails_closed(self):
        with self.assertRaisesRegex(AuthenticatedReportError, "drift"):
            validate_report_provenance({"games": report()["games"]}, expected(), label="certified", source_seat=0)

    def test_wrong_evaluator_fails_closed(self):
        value = report(); value["evaluator_sha256"] = "x" * 64
        with self.assertRaisesRegex(AuthenticatedReportError, "evaluator_sha256 drift"):
            validate_report_provenance(value, expected(), label="certified", source_seat=0)

    def test_wrong_candidate_fails_closed(self):
        value = report(); value["candidate"]["sha256"] = "x" * 64
        with self.assertRaisesRegex(AuthenticatedReportError, "candidate drift"):
            validate_report_provenance(value, expected(), label="certified", source_seat=0)

    def test_out_of_range_activation_step_fails_closed(self):
        value = report(); value["games"][0] = game(0, steps=10, diag=diagnostics(steps=[10]))
        with self.assertRaisesRegex(AuthenticatedReportError, "outside executed"):
            validate_report_provenance(value, expected(), label="certified", source_seat=0)

    def test_out_of_range_handoff_step_fails_closed(self):
        value = report(); value["games"][0] = game(0, steps=10, diag=diagnostics(handoff=10))
        with self.assertRaisesRegex(AuthenticatedReportError, "handoff step"):
            validate_report_provenance(value, expected(), label="certified", source_seat=0)

    def test_missing_expected_cell_fails_closed(self):
        value = report(); value["games"] = value["games"][:1]
        with self.assertRaisesRegex(AuthenticatedReportError, "cardinality"):
            validate_report_provenance(value, expected(), label="certified", source_seat=0)

    def test_duplicate_cell_fails_closed(self):
        value = report(); value["games"][1] = copy.deepcopy(value["games"][0])
        with self.assertRaisesRegex(AuthenticatedReportError, "unexpected or duplicate"):
            validate_report_provenance(value, expected(), label="certified", source_seat=0)

    def test_red_recheck_fails_closed(self):
        value = report(); value["reproducibility"]["same_trace_and_scores"] = False
        with self.assertRaisesRegex(AuthenticatedReportError, "recheck"):
            validate_report_provenance(value, expected(), label="certified", source_seat=0)


if __name__ == "__main__":
    unittest.main()
