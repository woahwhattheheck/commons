# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

import run_panel as panel


def game(opponent, seed, seat, scores, trace):
    return {"opponent": opponent, "seed": seed, "candidate_seat": seat,
            "status": "complete", "failure": None, "scores": scores,
            "trace_sha256": trace * 64}


def result(variant, games, candidate_sha="a" * 64):
    return {"variant": variant, "shard": 0, "returncode": 0,
            "report": {"schema_version": 1, "engine_ref": panel.ENGINE_REF,
                       "progress": {"state": "complete"},
                       "candidate": {"sha256": candidate_sha}, "opponents": {},
                       "engine_sha256": {}, "loader_sha256": "b" * 64,
                       "evaluator_sha256": "c" * 64, "limits": {}, "games": games}}


class PanelValidationTests(unittest.TestCase):
    def test_complete_grid_pairs_exact_cells(self):
        seeds = [1]; opponents = ["arlene"]
        base_games = [game("arlene", 1, 0, [100, 90], "a"),
                      game("arlene", 1, 1, [90, 100], "b")]
        cand_games = [game("arlene", 1, 0, [110, 90], "c"),
                      game("arlene", 1, 1, [90, 110], "d")]
        baseline, gate = panel.collect_games([result("baseline", base_games)],
                                             "baseline", seeds, opponents)
        candidate, cgate = panel.collect_games([result("candidate", cand_games)],
                                                "candidate", seeds, opponents)
        self.assertTrue(gate["valid"] and cgate["valid"])
        rows = panel.pair_games(baseline, candidate)
        summary = panel.summarize(rows)
        self.assertEqual(summary["cells"], 2)
        self.assertEqual(summary["mean_own_delta"], 10)
        self.assertEqual(summary["mean_margin_delta"], 10)
        self.assertEqual(summary["trace_changed_cells"], 2)

    def test_missing_cell_is_invalid_not_silently_averaged(self):
        games = [game("arlene", 1, 0, [100, 90], "a")]
        _, gate = panel.collect_games([result("baseline", games)],
                                      "baseline", [1], ["arlene"])
        self.assertFalse(gate["valid"])
        self.assertTrue(any("missing cells" in error for error in gate["errors"]))

    def test_failed_cell_is_not_accepted(self):
        games = [game("arlene", 1, 0, [100, 90], "a"),
                 {**game("arlene", 1, 1, [90, 100], "b"),
                  "status": "timeout", "failure": "deadline"}]
        accepted, gate = panel.collect_games([result("candidate", games)],
                                             "candidate", [1], ["arlene"])
        self.assertNotIn(("arlene", 1, 1), accepted)
        self.assertFalse(gate["valid"])

    def test_advance_gate_requires_v1_and_arlene(self):
        global_summary = {"trace_changed_cells": 12, "mean_own_delta": 100,
                          "mean_margin_delta": 120}
        strata = {name: {"mean_own_delta": 1} for name in panel.OPPONENTS}
        self.assertEqual(panel.verdict(global_summary, strata)["decision"], "ADVANCE")
        strata["v1"] = {"mean_own_delta": -1}
        self.assertEqual(panel.verdict(global_summary, strata)["decision"], "REJECT")


if __name__ == "__main__":
    unittest.main()
