# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import math
import unittest

import factorial_admission as admission


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_report(arm: str, score_fn=None, action_arm: str | None = None):
    seeds = [11, 22]
    opponents = {"arlene": {"entry": "arlene.py"}, "v1": {"entry": "v1.py"}}
    games = []
    for opponent in opponents:
        for seed in seeds:
            for seat in (0, 1):
                own, rival = (100.0, 90.0)
                if score_fn is not None:
                    own, rival = score_fn(opponent, seed, seat)
                label = action_arm if action_arm is not None else arm
                games.append(
                    {
                        "opponent": opponent,
                        "seed": seed,
                        "candidate_seat": seat,
                        "status": "complete",
                        "failure": None,
                        "scores": [own, rival] if seat == 0 else [rival, own],
                        "steps": 10,
                        "candidate_action_count": 10,
                        "candidate_action_sha256": digest(
                            f"{label}|{opponent}|{seed}|{seat}"
                        ),
                        "trace_sha256": digest(
                            f"trace|{arm}|{opponent}|{seed}|{seat}|{own}|{rival}"
                        ),
                    }
                )
    return {
        "schema_version": 1,
        "engine_ref": "engine-pin",
        "engine_sha256": {"engine.py": "engine-sha"},
        "loader_sha256": "loader-sha",
        "evaluator_sha256": "evaluator-sha",
        "python": "3.11-test",
        "platform": "linux",
        "agent_rng_seed": 123,
        "limits": {"action_rpc_seconds": 1.0},
        "candidate": {"entry": f"{arm}.py"},
        "opponents": opponents,
        "seeds": seeds,
        "games": games,
        "progress": {
            "state": "complete",
            "planned_games": len(games),
            "recorded_games": len(games),
            "active_game": None,
            "recheck_requested": True,
        },
        "reproducibility": {
            "checked": True,
            "same_trace_and_scores": True,
            "original_trace": digest(f"recheck|{arm}"),
            "replay_trace": digest(f"recheck|{arm}"),
        },
    }


def reports(*, both_scores=(105.0, 85.0)):
    control = build_report("control")
    own = build_report("own_only", lambda *_: (105.0, 90.0))
    strict = build_report("strict_only", lambda *_: (100.0, 85.0))
    both = build_report("both", lambda *_: both_scores)
    return {
        "control": control,
        "own_only": own,
        "strict_only": strict,
        "both": both,
    }


class AdmissionTests(unittest.TestCase):
    def test_exact_additive_composition_advances(self):
        result = admission.analyze_reports(reports())
        self.assertEqual(result["verdict"], "ADVANCE_COMPOSITION")
        self.assertEqual(result["total_games"], 32)
        self.assertEqual(result["interaction"]["classification"], "additive")
        self.assertEqual(result["interaction"]["overall"]["own"]["mean"], 0)
        self.assertEqual(result["interaction"]["overall"]["margin"]["mean"], 0)
        self.assertTrue(all(result["gates"].values()))
        self.assertFalse(result["promotion_authorized"])

    def test_synergy_is_measured_without_changing_gate_semantics(self):
        result = admission.analyze_reports(reports(both_scores=(107.0, 83.0)))
        self.assertEqual(result["verdict"], "ADVANCE_COMPOSITION")
        self.assertEqual(result["interaction"]["classification"], "synergistic")
        self.assertEqual(result["interaction"]["overall"]["own"]["mean"], 2)
        self.assertEqual(result["interaction"]["overall"]["margin"]["mean"], 4)

    def test_positive_total_hidden_antagonism_is_rejected(self):
        result = admission.analyze_reports(reports(both_scores=(103.0, 89.0)))
        self.assertEqual(result["verdict"], "REJECT")
        self.assertGreater(
            result["contrasts"]["both_vs_control"]["overall"]["margin"]["mean_delta"],
            0,
        )
        self.assertFalse(result["gates"]["safe_own_under_strict"])
        self.assertFalse(result["gates"]["safe_strict_under_own"])

    def test_new_loss_against_single_arm_is_rejected(self):
        value = reports()
        game = value["both"]["games"][0]
        seat = game["candidate_seat"]
        game["scores"] = [80.0, 90.0] if seat == 0 else [90.0, 80.0]
        result = admission.analyze_reports(value)
        self.assertEqual(result["verdict"], "REJECT")
        self.assertGreater(
            result["contrasts"]["own_under_strict"]["overall"]["new_losses"],
            0,
        )

    def test_inactive_factor_is_not_called_composition(self):
        value = reports()
        for own_game, control_game in zip(
            value["own_only"]["games"], value["control"]["games"]
        ):
            own_game["candidate_action_sha256"] = control_game[
                "candidate_action_sha256"
            ]
        result = admission.analyze_reports(value)
        self.assertEqual(result["verdict"], "INACTIVE")
        self.assertFalse(result["gates"]["own_factor_at_control"])

    def test_safety_violation_overrides_inactive_disposition(self):
        value = reports()
        for own_game, control_game in zip(
            value["own_only"]["games"], value["control"]["games"]
        ):
            own_game["candidate_action_sha256"] = control_game[
                "candidate_action_sha256"
            ]
        game = value["both"]["games"][0]
        seat = game["candidate_seat"]
        game["scores"] = [80.0, 90.0] if seat == 0 else [90.0, 80.0]
        result = admission.analyze_reports(value)
        self.assertEqual(result["verdict"], "REJECT")
        self.assertFalse(result["gates"]["own_factor_at_control"])
        self.assertFalse(result["gates"]["safe_own_under_strict"])

    def test_missing_cell_is_invalid(self):
        value = reports()
        value["both"]["games"].pop()
        with self.assertRaisesRegex(admission.AdmissionError, "both seats|expected"):
            admission.analyze_reports(value)

    def test_duplicate_cell_is_invalid(self):
        value = reports()
        value["strict_only"]["games"].append(
            copy.deepcopy(value["strict_only"]["games"][0])
        )
        with self.assertRaisesRegex(admission.AdmissionError, "duplicate game cell"):
            admission.analyze_reports(value)

    def test_one_seat_panel_is_invalid(self):
        value = reports()
        value["control"]["games"] = [
            game for game in value["control"]["games"]
            if game["candidate_seat"] == 0
        ]
        with self.assertRaisesRegex(admission.AdmissionError, "both seats"):
            admission.analyze_reports(value)

    def test_nonfinite_score_is_invalid(self):
        value = reports()
        value["own_only"]["games"][0]["scores"][0] = math.nan
        with self.assertRaisesRegex(admission.AdmissionError, "finite"):
            admission.analyze_reports(value)

    def test_failed_game_is_invalid(self):
        value = reports()
        value["strict_only"]["games"][0]["status"] = "failed"
        value["strict_only"]["games"][0]["failure"] = {"kind": "timeout"}
        with self.assertRaisesRegex(admission.AdmissionError, "incomplete game"):
            admission.analyze_reports(value)

    def test_identity_drift_is_invalid(self):
        value = reports()
        value["both"]["engine_ref"] = "other-engine"
        with self.assertRaisesRegex(admission.AdmissionError, "identity mismatch"):
            admission.analyze_reports(value)

    def test_action_count_must_bind_every_completed_step(self):
        value = reports()
        value["both"]["games"][0]["candidate_action_count"] = 9
        with self.assertRaisesRegex(admission.AdmissionError, "action count/step mismatch"):
            admission.analyze_reports(value)

    def test_reproducibility_recheck_is_mandatory(self):
        value = reports()
        value["control"]["reproducibility"]["same_trace_and_scores"] = False
        with self.assertRaisesRegex(admission.AdmissionError, "reproducibility"):
            admission.analyze_reports(value)


if __name__ == "__main__":
    unittest.main()
