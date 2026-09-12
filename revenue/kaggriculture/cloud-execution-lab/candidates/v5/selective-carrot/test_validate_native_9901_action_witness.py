# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "native9901_validator", HERE / "validate_native_9901_action_witness.py"
)
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)


def signed_report():
    authority = {
        "evaluator": {"path": "/tmp/evaluate.py", "sha256": v.EXPECTED["evaluator"]},
        "loader": {"path": "/tmp/loader.py", "sha256": v.EXPECTED["loader"]},
        "engine_sha256": copy.deepcopy(v.EXPECTED["engine"]),
        "left_archive": {"path": "/tmp/v31.tar.gz", "sha256": v.EXPECTED["left_archive"]},
        "right_archive": {"path": "/tmp/production-v3.tar.gz", "sha256": v.EXPECTED["right_archive"]},
        "left_entry_sha256": v.EXPECTED["left_entry"],
        "right_entry_sha256": v.EXPECTED["right_entry"],
        "opponent_entry_sha256": v.EXPECTED["opponent_entry"],
        "left_label": "V3.1",
        "right_label": "production-v3",
        "opponent_label": "apex_v7",
        "seed": v.EXPECTED["seed"],
        "rng_seed": v.EXPECTED["rng_seed"],
        "seats": [0, 1],
        "timeouts": copy.deepcopy(v.EXPECTED["timeouts"]),
    }
    rows = []
    for seat in (0, 1):
        candidate = 360 + seat
        rows.append({
            "candidate_seat": seat,
            "left_result": {
                "status": "complete",
                "candidate_seat": seat,
                "scores": copy.deepcopy(v.EXPECTED_SCORES[seat]["left"]),
                "steps": v.EXPECTED["steps"],
            },
            "right_result": {
                "status": "complete",
                "candidate_seat": seat,
                "scores": copy.deepcopy(v.EXPECTED_SCORES[seat]["right"]),
                "steps": v.EXPECTED["steps"],
            },
            "comparison": {
                "steps": v.EXPECTED["steps"],
                "first_candidate_action_divergence_step": candidate,
                "first_candidate_observation_divergence_step": candidate + 1,
                "first_opponent_action_divergence_step": candidate + 2,
                "first_opponent_observation_divergence_step": candidate + 3,
                "first_any_action_divergence_step": candidate,
                "all_actions_identical": False,
                "candidate_action_is_first_observed_divergence": True,
            },
        })
    report = {
        "schema": v.SCHEMA,
        "authority": authority,
        "authority_sha256": v._digest(authority),
        "rows": rows,
    }
    report["report_sha256"] = v._digest(report)
    return report


def resign(report):
    report["authority_sha256"] = v._digest(report["authority"])
    report.pop("report_sha256", None)
    report["report_sha256"] = v._digest(report)
    return report


class Native9901AuthorityTests(unittest.TestCase):
    def test_exact_retained_authority_passes_and_surfaces_causal_labels(self):
        result = v.validate(signed_report())
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["retained_terminal_scores_reproduced"])
        self.assertEqual(result["first_any_action_divergence_step"], {"0": 360, "1": 361})
        self.assertEqual(
            result["candidate_action_is_first_observed_divergence"],
            {"0": True, "1": True},
        )
        self.assertTrue(result["causal_candidate_first_both_seats"])

    def test_opponent_first_still_passes_custody_but_is_not_causal_positive(self):
        report = signed_report()
        comparison = report["rows"][1]["comparison"]
        comparison["first_candidate_action_divergence_step"] = 365
        comparison["first_candidate_observation_divergence_step"] = 366
        comparison["first_opponent_action_divergence_step"] = 361
        comparison["first_opponent_observation_divergence_step"] = 362
        comparison["first_any_action_divergence_step"] = 361
        comparison["candidate_action_is_first_observed_divergence"] = False
        resign(report)
        result = v.validate(report)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["candidate_action_is_first_observed_divergence"]["1"])
        self.assertFalse(result["causal_candidate_first_both_seats"])

    def test_resigned_forged_causal_label_rejects(self):
        report = signed_report()
        comparison = report["rows"][1]["comparison"]
        comparison["first_candidate_action_divergence_step"] = 365
        comparison["first_candidate_observation_divergence_step"] = 366
        comparison["first_opponent_action_divergence_step"] = 361
        comparison["first_opponent_observation_divergence_step"] = 362
        comparison["first_any_action_divergence_step"] = 361
        comparison["candidate_action_is_first_observed_divergence"] = True
        resign(report)
        with self.assertRaisesRegex(v.ValidationError, "causal divergence label inconsistent"):
            v.validate(report)

    def test_resigned_inconsistent_first_action_summary_rejects(self):
        report = signed_report()
        report["rows"][0]["comparison"]["first_any_action_divergence_step"] = 100
        resign(report)
        with self.assertRaisesRegex(v.ValidationError, "first action divergence summary inconsistent"):
            v.validate(report)

    def test_missing_causal_label_rejects_ambiguous_receipt(self):
        report = signed_report()
        report["rows"][0]["comparison"].pop("candidate_action_is_first_observed_divergence")
        resign(report)
        with self.assertRaisesRegex(v.ValidationError, "causal divergence label missing"):
            v.validate(report)

    def test_wrong_executed_entry_rejects_even_with_exact_archive(self):
        report = signed_report()
        report["authority"]["right_entry_sha256"] = "0" * 64
        resign(report)
        with self.assertRaisesRegex(v.ValidationError, "wrong production-v3 entry"):
            v.validate(report)

    def test_terminal_score_mismatch_rejects(self):
        report = signed_report()
        report["rows"][0]["right_result"]["scores"][0] -= 1.0
        resign(report)
        with self.assertRaisesRegex(v.ValidationError, "terminal score mismatch"):
            v.validate(report)

    def test_wrong_engine_member_rejects(self):
        report = signed_report()
        report["authority"]["engine_sha256"]["utils.py"] = "f" * 64
        resign(report)
        with self.assertRaisesRegex(v.ValidationError, "wrong engine authority"):
            v.validate(report)

    def test_wrong_or_duplicate_seat_panel_rejects(self):
        report = signed_report()
        report["rows"][1]["candidate_seat"] = 0
        resign(report)
        with self.assertRaisesRegex(v.ValidationError, "invalid/duplicate candidate seat"):
            v.validate(report)

    def test_no_action_divergence_rejects(self):
        report = signed_report()
        comparison = report["rows"][1]["comparison"]
        comparison["first_candidate_action_divergence_step"] = None
        comparison["first_opponent_action_divergence_step"] = None
        comparison["first_any_action_divergence_step"] = None
        comparison["all_actions_identical"] = True
        comparison["candidate_action_is_first_observed_divergence"] = False
        resign(report)
        with self.assertRaisesRegex(v.ValidationError, "lacks a real action divergence"):
            v.validate(report)

    def test_report_tamper_without_resign_rejects(self):
        report = signed_report()
        report["rows"][0]["comparison"]["first_any_action_divergence_step"] = 99
        with self.assertRaisesRegex(v.ValidationError, "report_sha256 mismatch"):
            v.validate(report)

    def test_wrong_timeout_rejects(self):
        report = signed_report()
        report["authority"]["timeouts"]["action"] = 2.0
        resign(report)
        with self.assertRaisesRegex(v.ValidationError, "wrong timeout authority"):
            v.validate(report)


if __name__ == "__main__":
    unittest.main()
