#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Regression contracts for evaluator process-exit custody."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
import titan_branch_tournament as tournament


ENGINE_REF = "a" * 40
SEEDS = [11, 17]


def _bundle(root: Path, name: str, role: str, marker: str) -> tournament.CandidateBundle:
    entry = root / f"{name}.py"
    entry.write_text("def agent(obs, cfg=None): return {}\n", encoding="utf-8")
    value = int(marker, 16)
    digest = lambda offset: f"{(value + offset) % 16:x}" * 64
    return tournament.CandidateBundle(
        name=name,
        commit=marker * 40,
        ref=marker * 40,
        role=role,
        bundle_root=root,
        entry_path=entry,
        callable_name="agent",
        archive_sha256=digest(0),
        archive_bytes=1,
        source_manifest_sha256=digest(1),
        source_manifest_bytes=1,
        receipt_sha256=digest(2),
        receipt_bytes=1,
        runtime_tree_sha256=digest(3),
        runtime_files=1,
        entry_sha256=tournament.sha256_bytes(entry.read_bytes()),
    )


def _complete_cells(score: float) -> dict[tuple[str, int, int], dict]:
    cells = {}
    for seed in SEEDS:
        for seat in (0, 1):
            scores = [100.0, 100.0]
            scores[seat] += score
            cells[("starter", seed, seat)] = {
                "opponent": "starter",
                "seed": seed,
                "candidate_seat": seat,
                "status": "complete",
                "scores": scores,
                "failure": None,
            }
    return cells


class EvaluatorExitCustodyTests(unittest.TestCase):
    def test_nonzero_exit_with_complete_cells_cannot_advance(self):
        with tempfile.TemporaryDirectory(prefix="titan-exit-ranking-") as temp:
            root = Path(temp)
            baseline = tournament.CandidateExecution(
                bundle=_bundle(root, "baseline", "baseline", "1"),
                report_path=None,
                stdout_path=root / "baseline.out",
                stderr_path=root / "baseline.err",
                returncode=0,
                wall_seconds=0.0,
                report_sha256=None,
                report_bytes=None,
                stdout_sha256="0" * 64,
                stderr_sha256="0" * 64,
                cells=_complete_cells(10.0),
                integrity_error=None,
            )
            failed = tournament.CandidateExecution(
                bundle=_bundle(root, "failed-evaluator", "challenger", "5"),
                report_path=None,
                stdout_path=root / "failed.out",
                stderr_path=root / "failed.err",
                returncode=17,
                wall_seconds=0.0,
                report_sha256=None,
                report_bytes=None,
                stdout_sha256="0" * 64,
                stderr_sha256="0" * 64,
                cells=_complete_cells(15.0),
                integrity_error=None,
            )
            opponents = [
                tournament.Opponent(
                    "starter",
                    "official_starter",
                    {"kind": "official_starter", "engine_ref": ENGINE_REF},
                )
            ]
            ranking = {
                "bootstrap_samples": 500,
                "confidence": 0.95,
                "bootstrap_seed": 5,
                "min_mean_delta": 0.0,
                "min_ci_lower_delta": 0.0,
                "min_worst_opponent_delta": 0.0,
            }
            rows, champion, promotable = tournament.build_rankings(
                [baseline, failed],
                baseline_name="baseline",
                opponents=opponents,
                seeds=SEEDS,
                ranking=ranking,
            )
            failed_row = next(row for row in rows if row["name"] == "failed-evaluator")
            self.assertFalse(failed.integrity_valid)
            self.assertFalse(failed_row["absolute"]["complete_grid"])
            self.assertFalse(failed_row["paired_vs_baseline"]["comparable"])
            self.assertEqual(failed_row["decision"], "HOLD_INCOMPLETE")
            self.assertFalse(failed_row["advance"])
            self.assertEqual(champion, "baseline")
            self.assertFalse(promotable)

    def test_execute_candidate_records_nonzero_exit_after_valid_report(self):
        with tempfile.TemporaryDirectory(prefix="titan-exit-execute-") as temp:
            root = Path(temp)
            output = root / "output"
            output.mkdir()
            engine = root / "engine"
            engine.mkdir()
            evaluator_script = root / "evaluate.py"
            evaluator_loader = root / "loader.py"
            evaluator_script.write_text("# evaluator fixture\n", encoding="utf-8")
            evaluator_loader.write_text("# loader fixture\n", encoding="utf-8")
            candidate = _bundle(root, "candidate", "challenger", "6")
            evaluator = tournament.EvaluatorMaterial(
                script=evaluator_script,
                loader=evaluator_loader,
                commit="b" * 40,
                sha256=tournament.sha256_bytes(evaluator_script.read_bytes()),
                loader_sha256=tournament.sha256_bytes(evaluator_loader.read_bytes()),
            )
            opponents = [
                tournament.Opponent(
                    "starter",
                    "official_starter",
                    {"kind": "official_starter", "engine_ref": ENGINE_REF},
                )
            ]
            engine_sha256 = {"engine.py": "e" * 64}

            def fake_run(args, **kwargs):
                report_path = Path(args[args.index("--output") + 1])
                report = {
                    "schema_version": 1,
                    "engine_ref": ENGINE_REF,
                    "engine_sha256": engine_sha256,
                    "evaluator_sha256": evaluator.sha256,
                    "loader_sha256": evaluator.loader_sha256,
                    "candidate": {"sha256": candidate.entry_sha256},
                    "opponents": {
                        "starter": {
                            "entry": "official_starter",
                            "engine_ref": ENGINE_REF,
                        }
                    },
                    "seeds": SEEDS,
                    "agent_rng_seed": 99,
                    "games": list(_complete_cells(15.0).values()),
                    "reproducibility": {
                        "checked": True,
                        "same_trace_and_scores": True,
                    },
                }
                report_path.write_text(json.dumps(report) + "\n", encoding="utf-8")
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=17,
                    stdout=b"complete report written\n",
                    stderr=b"postflight failed\n",
                )

            function_globals = tournament.execute_candidate.__globals__
            original_run = function_globals["_run"]
            function_globals["_run"] = fake_run
            try:
                execution = tournament.execute_candidate(
                    candidate,
                    evaluator=evaluator,
                    opponents=opponents,
                    seeds=SEEDS,
                    rng_seed=99,
                    engine_dir=engine,
                    engine_ref=ENGINE_REF,
                    engine_sha256=engine_sha256,
                    limits={
                        "action_timeout": 1.0,
                        "startup_timeout": 2.0,
                        "game_timeout": 3.0,
                        "episode_steps": 8,
                    },
                    recheck_first=True,
                    output_dir=output,
                    process_timeout=30.0,
                )
            finally:
                function_globals["_run"] = original_run

            self.assertEqual(execution.returncode, 17)
            self.assertIsNotNone(execution.cells)
            self.assertIsNotNone(execution.report_sha256)
            self.assertIn("evaluator exited with nonzero status 17", execution.integrity_error)
            self.assertFalse(execution.integrity_valid)
            description = tournament.describe_execution(
                execution, tournament.expected_cell_keys(opponents, SEEDS)
            )
            self.assertFalse(description["complete_grid"])
            self.assertIsNone(description["mean_margin"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
