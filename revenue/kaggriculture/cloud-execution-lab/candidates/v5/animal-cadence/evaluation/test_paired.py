# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cadence_paired", HERE / "paired.py")
paired = importlib.util.module_from_spec(spec); spec.loader.exec_module(paired)


def game(score0=10.0, score1=5.0):
    return {"status": "complete", "steps": 719, "scores": [score0, score1]}


METRICS_SCHEMA = "titan-v5/animal-cadence/matched-eval-agent-metrics/v1"

def cell(seed=1, seat=0, engagement=1):
    b, c = game(), game(11.0, 5.0)
    bm, cm = paired.margin(b, seat), paired.margin(c, seat)
    bs, cs = paired.own_score(b, seat), paired.own_score(c, seat)
    return {
        "cell_id": f"apex_v7-s{seed}-p{seat}", "opponent":"apex_v7", "seed":seed, "seat":seat,
        "baseline":b, "candidate":c, "baseline_margin":bm, "candidate_margin":cm,
        "margin_delta":cm-bm, "baseline_own_score":bs, "candidate_own_score":cs,
        "own_score_delta":cs-bs, "baseline_outcome":paired.outcome(bm), "candidate_outcome":paired.outcome(cm),
        "complete_pair":True, "candidate_metrics":{"schema":METRICS_SCHEMA,"authority_engagements":engagement,"candidate_engagements":engagement,"feed_actions_suppressed":engagement,"unique_tile_wheat_saved":engagement,"errors":{}},
        "baseline_animal_escapes":[], "candidate_animal_escapes":[], "animal_escape_delta":0,
        "care_bonus_divergence_steps":0,
    }


class MatchedEvalTests(unittest.TestCase):
    def report(self, cells):
        opponents = sorted({c["opponent"] for c in cells})
        seeds = sorted({c["seed"] for c in cells})
        seats = sorted({c["seat"] for c in cells})
        return {"schema": paired.SCHEMA, "run":{"expected_cells":len(cells), "opponent_names":opponents, "seeds":seeds, "seats":seats}, "cells":cells, "summary":paired.summarize(cells)}

    def test_complete_exact_cells_validate(self):
        self.assertTrue(paired.validate_report(self.report([cell()])))

    def test_duplicate_cell_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "duplicate_cell"):
            paired.validate_report(self.report([cell(), cell()]))

    def test_incomplete_cell_fails_closed(self):
        value = cell(); value["candidate"]["status"] = "failed"
        with self.assertRaisesRegex(ValueError, "incomplete_cell"):
            paired.validate_report(self.report([value]))

    def test_nonfinite_metric_fails_closed(self):
        value = cell(); value["margin_delta"] = float("nan")
        with self.assertRaisesRegex(ValueError, "nonfinite_metric"):
            paired.validate_report(self.report([value]))

    def test_unmatched_count_fails_closed(self):
        report = self.report([cell()]); report["run"]["expected_cells"] = 2
        with self.assertRaisesRegex(ValueError, "unmatched_cells"):
            paired.validate_report(report)

    def test_zero_candidate_engagement_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "zero_candidate_engagement"):
            paired.validate_report(self.report([cell(engagement=0)]))

    def test_outcomes_and_deltas(self):
        value = cell()
        self.assertEqual(value["baseline_outcome"], "W")
        self.assertEqual(value["candidate_outcome"], "W")
        self.assertEqual(value["margin_delta"], 1.0)
        self.assertEqual(value["own_score_delta"], 1.0)

    def test_mixed_identity_fails_closed(self):
        report = self.report([cell()]); report["run"]["opponent_names"] = ["apex_v7", "arlene_v14"]; report["run"]["expected_cells"] = 2
        with self.assertRaisesRegex(ValueError, "unmatched_cells"):
            paired.validate_report(report)

    def test_candidate_adapter_error_fails_closed(self):
        value = cell(); value["candidate_metrics"]["errors"] = {"RuntimeError:oops": 1}
        with self.assertRaisesRegex(ValueError, "candidate_adapter_errors"):
            paired.validate_report(self.report([value]))

    def test_canonical_game_strips_timing_noise(self):
        raw = {"status":"complete","steps":719,"scores":[1,0],"wall_seconds":9.9,"driver_cpu_seconds":1.2,
               "actors":[{"calls":720,"timeouts":0,"errors":0,"invalid_actions":0,"exit_code":0,"cpu_seconds":3.3}]}
        projected = paired.canonical_game(raw)
        self.assertNotIn("wall_seconds", projected)
        self.assertNotIn("driver_cpu_seconds", projected)
        self.assertNotIn("cpu_seconds", projected["actors"][0])
        self.assertEqual(projected["actors"][0]["calls"], 720)

    def test_animal_escape_detector_is_specific_to_second_unfed_transition(self):
        tracker = {"last":{"1,2":{"animal":"COW","consecutive_unfed":1,"fed_today":False}}, "animal_escapes":[], "care_bonus_by_step":[], "animal_count_by_step":[]}
        state = [type("S", (), {"observation":{"farms":[{"tiles":[[]]}, {"tiles":[[]]}]}})()]
        paired.observe_animals(state, 0, tracker, 24)
        self.assertEqual(tracker["animal_escapes"][0]["animal"], "COW")


if __name__ == "__main__": unittest.main()
