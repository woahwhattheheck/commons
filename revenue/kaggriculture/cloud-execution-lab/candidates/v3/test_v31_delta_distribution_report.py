from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "v31_delta_distribution_report", HERE / "v31_delta_distribution_report.py"
)
assert SPEC and SPEC.loader
reporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reporter)


def cell(opponent, seed, seat, baseline, candidate, **extra):
    row = {
        "opponent": opponent,
        "seed": seed,
        "seat": seat,
        "baseline": {"own": baseline[0], "rival": baseline[1]},
        "candidate": {"own": candidate[0], "rival": candidate[1]},
    }
    row.update(extra)
    return row


class DeltaDistributionReportTests(unittest.TestCase):
    def test_recomputes_delta_and_exposes_poisoned_supplied_value(self):
        report = reporter.analyze(
            [cell("agent-a", 7, 0, (100, 90), (120, 95), delta_m=-999)]
        )
        self.assertEqual(report["delta_m"]["mean"], 15.0)
        self.assertEqual(report["delta_m"]["supplied_mismatch_count"], 1)
        mismatch = report["delta_m"]["supplied_mismatches"][0]
        self.assertEqual(mismatch["supplied"], -999.0)
        self.assertEqual(mismatch["recomputed"], 15.0)

    def test_rejects_duplicate_and_nonfinite_cells(self):
        row = cell("agent-a", 7, 0, (10, 9), (11, 9))
        with self.assertRaisesRegex(reporter.DataError, "duplicate logical cell"):
            reporter.analyze([row, dict(row)])
        bad = cell("agent-a", 8, 0, (float("nan"), 9), (11, 9))
        with self.assertRaisesRegex(reporter.DataError, "finite"):
            reporter.analyze([bad])

    def test_transitions_seat_opponent_and_activation_strata(self):
        rows = [
            cell("agent-a", 1, 0, (10, 9), (8, 9), activations={"fertilizer": 2}),
            cell(
                "agent-a",
                1,
                1,
                (5, 5),
                (7, 5),
                diagnostics={"activations": {"fertilizer": 0}},
            ),
            cell("agent-b", 2, 0, (4, 5), (6, 5)),
        ]
        report = reporter.analyze(rows)
        self.assertEqual(report["cells"], 3)
        self.assertAlmostEqual(report["delta_m"]["mean"], 2.0 / 3.0)
        self.assertEqual(
            report["outcomes"]["transitions"],
            {"L->W": 1, "T->W": 1, "W->L": 1},
        )
        self.assertEqual(len(report["outcomes"]["new_losses"]), 1)
        self.assertEqual(len(report["outcomes"]["lost_wins"]), 1)
        self.assertEqual(report["by_seat"]["0"]["count"], 2)
        self.assertEqual(report["by_opponent"]["agent-a"]["count"], 2)
        feature = report["activations"]["fertilizer"]
        self.assertEqual(feature["active"]["count"], 1)
        self.assertEqual(feature["inactive"]["count"], 1)
        self.assertEqual(feature["unknown_count"], 1)

    def test_separate_arm_rows_pair_raw_evaluator_scores_by_candidate_seat(self):
        document = {
            "baseline": [
                {"opponent": "a", "seed": 1, "seat": 0, "own": 10, "rival": 9},
                {"opponent": "a", "seed": 1, "candidate_seat": 1, "scores": [8, 10]},
            ],
            "candidate": [
                {
                    "opponent": "a",
                    "seed": 1,
                    "candidate_seat": 1,
                    "scores": [7, 12],
                    "activations": {"x": 1},
                },
                {"opponent": "a", "seed": 1, "seat": 0, "own": 12, "rival": 9},
            ],
        }
        report = reporter.analyze(reporter.load_records(document))
        self.assertEqual(report["cells"], 2)
        self.assertEqual(report["delta_m"]["mean"], 2.5)
        self.assertEqual(report["by_seat"]["1"]["mean_delta_m"], 3.0)
        self.assertEqual(report["activations"]["x"]["active"]["count"], 1)
        self.assertEqual(report["activations"]["x"]["unknown_count"], 1)

        broken = {"baseline": document["baseline"], "candidate": document["candidate"][:1]}
        with self.assertRaisesRegex(reporter.DataError, "arm cell sets differ"):
            reporter.load_records(broken)

    def test_top_level_raw_score_vectors_are_seat_ordered(self):
        report = reporter.analyze(
            [
                {
                    "opponent": "raw-official",
                    "seed": 2,
                    "candidate_seat": 1,
                    "baseline_scores": [90, 120],
                    "candidate_scores": [80, 130],
                }
            ]
        )
        self.assertEqual(report["delta_m"]["mean"], 20.0)
        self.assertEqual(report["delta_m"]["best_cell"]["baseline_margin"], 30.0)
        self.assertEqual(report["delta_m"]["best_cell"]["candidate_margin"], 50.0)

    def test_conflicting_identity_aliases_fail_closed(self):
        row = cell("a", 1, 0, (10, 9), (11, 9))
        row["candidate_seat"] = 1
        with self.assertRaisesRegex(reporter.DataError, "conflicting seat aliases"):
            reporter.analyze([row])

        row = cell("a", 1, 0, (10, 9), (11, 9))
        row["opponent_name"] = "b"
        with self.assertRaisesRegex(reporter.DataError, "conflicting opponent aliases"):
            reporter.analyze([row])

        row = cell("a", 1, 0, (10, 9), (11, 9))
        row["game_seed"] = 2
        with self.assertRaisesRegex(reporter.DataError, "conflicting seed aliases"):
            reporter.analyze([row])

    def test_conflicting_score_representations_fail_closed(self):
        row = cell("a", 1, 0, (10, 9), (11, 9))
        row["baseline_scores"] = [9, 10]
        with self.assertRaisesRegex(reporter.DataError, "conflicting baseline score representations"):
            reporter.analyze([row])

        row = cell("a", 1, 0, (10, 9), (11, 9))
        row["candidate"]["scores"] = [99, 1]
        with self.assertRaisesRegex(reporter.DataError, "conflicting candidate score representations"):
            reporter.analyze([row])

    def test_blank_seed_and_conflicting_delta_aliases_fail_closed(self):
        row = cell("a", "", 0, (10, 9), (11, 9))
        with self.assertRaisesRegex(reporter.DataError, "non-empty string"):
            reporter.analyze([row])

        row = cell("a", 1, 0, (10, 9), (11, 9), delta_m=1)
        row["deltaM"] = 2
        with self.assertRaisesRegex(reporter.DataError, "conflicting supplied delta aliases"):
            reporter.analyze([row])

    def test_policy_is_explicit_and_separate_from_measurement(self):
        report = reporter.analyze(
            [
                cell("a", 1, 0, (10, 9), (8, 9), delta_m=-2),
                cell("a", 1, 1, (10, 9), (13, 9), delta_m=3),
            ]
        )
        self.assertEqual(reporter.policy_failures(report), [])
        failures = reporter.policy_failures(
            report,
            require_no_new_losses=True,
            require_no_lost_wins=True,
            min_mean_delta=1.0,
        )
        self.assertEqual(len(failures), 3)
        self.assertEqual(
            reporter.policy_failures(report, strict_supplied_delta=True), []
        )

        poisoned = reporter.analyze(
            [cell("a", 2, 0, (10, 9), (11, 9), delta_m=500)]
        )
        self.assertTrue(
            reporter.policy_failures(poisoned, strict_supplied_delta=True)
        )

    def test_cli_exit_codes_distinguish_data_and_policy_failure(self):
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence.json"
            evidence.write_text(
                json.dumps([cell("a", 1, 0, (10, 9), (8, 9))]),
                encoding="utf-8",
            )
            self.assertEqual(
                reporter.main([str(evidence), "--require-no-new-losses"]), 1
            )
            evidence.write_text("{broken", encoding="utf-8")
            self.assertEqual(reporter.main([str(evidence)]), 2)


if __name__ == "__main__":
    unittest.main()