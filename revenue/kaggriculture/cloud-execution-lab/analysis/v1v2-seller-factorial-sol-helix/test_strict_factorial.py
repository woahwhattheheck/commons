# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import strict_factorial as strict
from strict_test_fixture import Fixture, HEAD, _write_json


class StrictFactorialTests(unittest.TestCase):
    def test_full_exact_artifact_is_admitted_and_factorial_math_survives(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp))
            report = strict.build_report(fixture.paths, head=HEAD)
            self.assertEqual(report["design"]["total_cells"], 128)
            self.assertEqual(report["selection"]["selected_arm"], "both")
            self.assertAlmostEqual(report["factor_effects"]["carry_main"]["group_own_effect"]["mean"], 15.0)
            self.assertAlmostEqual(report["factor_effects"]["force_end_main"]["group_own_effect"]["mean"], 10.0)
            self.assertAlmostEqual(report["factor_effects"]["interaction"]["group_own_effect"]["mean"], 10.0)

    def test_parent_style_partial_grid_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp))
            report = fixture.report("both")
            report["seeds"] = report["seeds"][:2]
            report["expected_cells"] = 16
            report["gate"].update(expected=16, accepted=16)
            report["games"] = report["games"][:16]
            fixture.write_report("both", report)
            with self.assertRaisesRegex(strict.AdmissionError, "seed tuple mismatch"):
                strict.build_report(fixture.paths, head=HEAD)

    def test_boolean_seat_is_rejected_before_python_aliasing(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp))
            shard_path = fixture.shard_path("carry_095")
            shard = json.loads(shard_path.read_text(encoding="utf-8"))
            shard["games"][0]["candidate_seat"] = False
            _write_json(shard_path, shard)
            report = fixture.report("carry_095")
            report["games"][0]["candidate_seat"] = False
            fixture.write_report("carry_095", report)
            with self.assertRaisesRegex(strict.AdmissionError, "literal integer"):
                strict.build_report(fixture.paths, head=HEAD)

    def test_rival_or_state_trace_change_cannot_impersonate_candidate_activation(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp), action_same=frozenset({"carry_095"}))
            report = strict.build_report(fixture.paths, head=HEAD)
            candidate = report["selection"]["candidates"]["carry_095"]
            self.assertFalse(candidate["checks"]["candidate_actions_activated"])
            self.assertFalse(candidate["eligible"])
            self.assertEqual(report["arm_results"]["carry_095"]["whole_trace_changed_cells"], 32)

    def test_own_cash_gain_can_advance_when_margin_delta_is_negative_without_new_losses(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(
                Path(temp),
                deltas={"control": 0.0, "carry_095": 5.0, "force_end": 0.0, "both": 0.0},
                rival_deltas={"control": 0.0, "carry_095": 20.0, "force_end": 0.0, "both": 0.0},
            )
            report = strict.build_report(fixture.paths, head=HEAD)
            candidate = report["selection"]["candidates"]["carry_095"]
            self.assertLess(report["arm_results"]["carry_095"]["group_margin_delta"]["mean"], 0)
            self.assertEqual(report["arm_results"]["carry_095"]["new_loss_cells"], 0)
            self.assertTrue(candidate["eligible"])
            self.assertEqual(report["selection"]["selected_arm"], "carry_095")

    def test_seat_skewed_gain_cannot_green_universal_seat_one_regression(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(
                Path(temp),
                deltas={
                    "control": 0.0,
                    "carry_095": {0: 1200.0, 1: -800.0},
                    "force_end": 0.0,
                    "both": 0.0,
                },
            )
            report = strict.build_report(fixture.paths, head=HEAD)
            candidate = report["selection"]["candidates"]["carry_095"]
            self.assertGreater(candidate["rank_metric_mean_group_own_delta"], 0)
            self.assertFalse(candidate["checks"]["every_opponent_seat_nonnegative"])
            self.assertFalse(candidate["eligible"])
            self.assertEqual(report["selection"]["selected_arm"], "control")

    def test_duplicate_evaluator_invocation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp))
            first = json.loads(fixture.shard_path("control", 0).read_text(encoding="utf-8"))
            second_path = fixture.shard_path("control", 1)
            second = json.loads(second_path.read_text(encoding="utf-8"))
            second["invocation_id"] = first["invocation_id"]
            _write_json(second_path, second)
            with self.assertRaisesRegex(strict.AdmissionError, "distinct evaluator invocations"):
                strict.build_report(fixture.paths, head=HEAD)

    def test_nonzero_evaluator_exit_cannot_mint_complete_arm(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp))
            report = fixture.report("force_end")
            report["completed_shards"][1]["returncode"] = 17
            fixture.write_report("force_end", report)
            with self.assertRaisesRegex(strict.AdmissionError, "nonzero shard completion"):
                strict.build_report(fixture.paths, head=HEAD)

    def test_tiny_self_consistent_episode_lifecycle_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp))
            shard_path = fixture.shard_path("both")
            shard = json.loads(shard_path.read_text(encoding="utf-8"))
            key = (shard["games"][0]["opponent"], shard["games"][0]["seed"], shard["games"][0]["candidate_seat"])
            shard["games"][0].update(episode_steps=2, steps=1, candidate_action_count=1)
            for actor in shard["games"][0]["actors"]:
                actor["calls"] = 1
            _write_json(shard_path, shard)
            report = fixture.report("both")
            for game in report["games"]:
                if (game["opponent"], game["seed"], game["candidate_seat"]) == key:
                    game.update(episode_steps=2, steps=1, candidate_action_count=1)
                    for actor in game["actors"]:
                        actor["calls"] = 1
                    break
            fixture.write_report("both", report)
            with self.assertRaisesRegex(strict.AdmissionError, "candidate_action_count mismatch|lifecycle mismatch"):
                strict.build_report(fixture.paths, head=HEAD)

    def test_evaluator_receipt_distinguishes_embedded_old_bytes_from_unconsumed_sites(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp))
            receipt_path = (Path(temp) / "evidence" / "carry_095"
                            / "carry_095-shards" / "EVALUATOR-MATERIALIZATION.json")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["patched"]["patches"][1]["old_occurrences_after_raw"] = 2
            _write_json(receipt_path, receipt)
            with self.assertRaisesRegex(strict.AdmissionError, "patch cardinality receipt mismatch"):
                strict.build_report(fixture.paths, head=HEAD)

    def test_retained_bundle_tamper_is_rejected_even_if_arm_json_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp))
            scheduler = Path(temp) / "arms" / "force_end" / "scheduler.py"
            scheduler.write_text(scheduler.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
            with self.assertRaisesRegex(strict.AdmissionError, "entry closure mismatch"):
                strict.build_report(fixture.paths, head=HEAD)

    def test_import_guard_rejects_preloaded_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp))
            entry = Path(temp) / "arms" / "control" / "bound_entry.py"
            origins = strict.verify_entry_runtime(entry)
            self.assertTrue(origins["candidate"].endswith("candidate.py"))
            self.assertTrue(origins["scheduler"].endswith("scheduler.py"))

    def test_raw_report_and_arm_summary_must_match_exactly(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp))
            report = fixture.report("both")
            report["games"][0]["scores"][0] += 1
            fixture.write_report("both", report)
            with self.assertRaisesRegex(strict.AdmissionError, "not byte-semantically derived"):
                strict.build_report(fixture.paths, head=HEAD)

    def test_cross_arm_closure_alias_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = Fixture(Path(temp))
            arms = {
                arm: strict.validate_arm(fixture.paths[arm], arm, HEAD)
                for arm in strict.ARMS
            }
            arms["both"]["materialization"]["closure_sha256"] = (
                arms["carry_095"]["materialization"]["closure_sha256"]
            )
            with self.assertRaisesRegex(strict.AdmissionError, "distinct closures"):
                strict._shared_environment(arms)

    def test_strict_json_rejects_duplicate_and_nonfinite_tokens(self):
        with tempfile.TemporaryDirectory() as temp:
            duplicate = Path(temp) / "duplicate.json"
            duplicate.write_text('{"a":1,"a":2}\n', encoding="utf-8")
            with self.assertRaisesRegex(strict.AdmissionError, "duplicate JSON key"):
                strict.load_json(duplicate)
            nonfinite = Path(temp) / "nonfinite.json"
            nonfinite.write_text('{"a":NaN}\n', encoding="utf-8")
            with self.assertRaisesRegex(strict.AdmissionError, "non-finite JSON token"):
                strict.load_json(nonfinite)


if __name__ == "__main__":
    unittest.main()
