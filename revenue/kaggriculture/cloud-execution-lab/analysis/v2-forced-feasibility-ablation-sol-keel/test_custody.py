from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
KAG = LAB.parent
FROZEN_V2 = LAB / "runtime" / "variants" / "v2"
EVALUATOR = KAG / "cloud-eval" / "evaluate.py"

import bind_execution
import compare_bound
import materialize
import materialize_evaluator


def write_json(path: Path, value: dict) -> None:
    materialize._load_base().atomic_write(
        path,
        (
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False)
            + "\n"
        ).encode("utf-8"),
    )


def build_artifacts(root: Path) -> dict:
    ablation = root / "materialized-ablation"
    materialization = materialize.materialize(FROZEN_V2, ablation)
    materialization_path = root / "MATERIALIZATION.json"
    write_json(materialization_path, materialization)

    arms_root = root / "arms"
    binding = bind_execution.bind_execution(
        FROZEN_V2,
        ablation,
        materialization_path,
        arms_root,
    )
    binding_path = root / "EXECUTION-BINDING.json"
    write_json(binding_path, binding)

    patched_evaluator = root / "evaluate-bound.py"
    evaluator = materialize_evaluator.materialize_evaluator(
        EVALUATOR, patched_evaluator
    )
    evaluator_path = root / "EVALUATOR-MATERIALIZATION.json"
    write_json(evaluator_path, evaluator)
    return {
        "ablation": ablation,
        "materialization": materialization,
        "materialization_path": materialization_path,
        "arms_root": arms_root,
        "binding": binding,
        "binding_path": binding_path,
        "patched_evaluator": patched_evaluator,
        "evaluator": evaluator,
        "evaluator_path": evaluator_path,
    }


def hex_digest(*parts: object) -> str:
    return hashlib.sha256(
        ":".join(str(part) for part in parts).encode("utf-8")
    ).hexdigest()


def synthetic_report(
    artifacts: dict,
    arm: str,
    *,
    own_delta_by_seat: dict[int, float] | None = None,
    action_changed: bool = False,
    whole_trace_changed: bool = False,
) -> dict:
    if own_delta_by_seat is None:
        own_delta_by_seat = {0: 0.0, 1: 0.0}
    environment = compare_bound.expected_environment()
    wrapper_sha = artifacts["binding"]["arms"][arm]["wrapper_sha256"]
    invocation = "1" * 32 if arm == "control" else "2" * 32
    games = []
    for opponent in ("arlene", "v1"):
        for seed in compare_bound.EXPECTED_SEEDS:
            for seat in (0, 1):
                own_delta = (
                    0.0
                    if arm == "control"
                    else float(own_delta_by_seat[seat])
                )
                scores = [100.0, 100.0]
                scores[seat] += own_delta
                baseline_action = hex_digest("action", opponent, seed, seat)
                action_digest = (
                    hex_digest("ablation-action", opponent, seed, seat)
                    if arm == "ablation" and action_changed
                    else baseline_action
                )
                baseline_trace = hex_digest("trace", opponent, seed, seat)
                trace_digest = (
                    hex_digest("ablation-trace", opponent, seed, seat)
                    if arm == "ablation" and whole_trace_changed
                    else baseline_trace
                )
                games.append(
                    {
                        "opponent": opponent,
                        "seed": seed,
                        "candidate_seat": seat,
                        "status": "complete",
                        "failure": None,
                        "steps": compare_bound.EXPECTED_ACTIONS,
                        "episode_steps": compare_bound.EXPECTED_EPISODE_STEPS,
                        "scores": scores,
                        "trace_sha256": trace_digest,
                        "candidate_action_sha256": action_digest,
                        "candidate_action_count": compare_bound.EXPECTED_ACTIONS,
                        "daily_bank": [{"step": 0, "bank": scores}],
                    }
                )
    return {
        "schema_version": 1,
        "invocation_id": invocation,
        "engine_ref": environment["engine_ref"],
        "engine_sha256": environment["engine_sha256"],
        "loader_sha256": environment["loader_sha256"],
        "evaluator_sha256": artifacts["evaluator"]["patched"]["sha256"],
        "candidate": {
            "entry": "bound_entry.py",
            "callable": "agent",
            "sha256": wrapper_sha,
        },
        "opponents": environment["opponents"],
        "seeds": list(compare_bound.EXPECTED_SEEDS),
        "agent_rng_seed": compare_bound.EXPECTED_RNG_SEED,
        "python": "3.11.14 synthetic",
        "platform": "linux",
        "resource_usage": {},
        "limits": dict(compare_bound.EXPECTED_LIMITS),
        "method": "Official interpreter synthetic contract fixture",
        "summary": {},
        "games": games,
        "reproducibility": None,
        "progress": {
            "state": "complete",
            "phase": "finalize",
            "planned_games": 16,
            "recorded_games": 16,
            "active_game": None,
            "recheck_requested": False,
        },
    }


def compare_reports(
    artifacts: dict,
    control: dict,
    candidate: dict,
) -> dict:
    return compare_bound.compare_bound(
        control,
        candidate,
        artifacts["materialization"],
        artifacts["binding"],
        artifacts["evaluator"],
        materialization_path=artifacts["materialization_path"],
        arms_root=artifacts["arms_root"],
        patched_evaluator_path=artifacts["patched_evaluator"],
        git_head="a" * 40,
    )


class ExecutionCustodyContracts(unittest.TestCase):
    def test_exact_closures_receive_distinct_live_wrappers(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = build_artifacts(Path(directory))
            arms = compare_bound.validate_binding(
                artifacts["binding"],
                artifacts["materialization_path"],
                artifacts["materialization"],
            )
            compare_bound.validate_live_arms(arms, artifacts["arms_root"])
            self.assertNotEqual(
                arms["control"]["payload_closure_sha256"],
                arms["ablation"]["payload_closure_sha256"],
            )
            self.assertNotEqual(
                arms["control"]["wrapper_sha256"],
                arms["ablation"]["wrapper_sha256"],
            )
            self.assertEqual(
                arms["control"]["payload_closure_sha256"],
                artifacts["materialization"]["source"]["closure_sha256"],
            )
            self.assertEqual(
                arms["ablation"]["payload_closure_sha256"],
                artifacts["materialization"]["ablation"]["closure_sha256"],
            )

    def test_payload_tamper_fails_inside_actor_wrapper_before_import(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = build_artifacts(Path(directory))
            scheduler = (
                artifacts["arms_root"]
                / "control"
                / "payload"
                / "scheduler.py"
            )
            scheduler.write_bytes(scheduler.read_bytes() + b"\n# tamper\n")
            wrapper = (
                artifacts["arms_root"] / "control" / "bound_entry.py"
            )
            result = subprocess.run(
                [sys.executable, "-B", str(wrapper)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bound payload closure mismatch", result.stderr)
            with self.assertRaises(compare_bound.BoundCompareError):
                compare_bound.validate_live_arms(
                    compare_bound.validate_binding(
                        artifacts["binding"],
                        artifacts["materialization_path"],
                        artifacts["materialization"],
                    ),
                    artifacts["arms_root"],
                )

    def test_exact_evaluator_patch_is_live_and_source_immutable(self):
        before = EVALUATOR.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            artifacts = build_artifacts(Path(directory))
            digest = compare_bound.validate_evaluator(
                artifacts["evaluator"], artifacts["patched_evaluator"]
            )
            self.assertEqual(
                digest, artifacts["evaluator"]["patched"]["sha256"]
            )
            self.assertEqual(
                len(artifacts["evaluator"]["patched"]["patches"]), 3
            )
            patched = artifacts["patched_evaluator"].read_text(
                encoding="utf-8"
            )
            self.assertIn("candidate_action_sha256", patched)
            self.assertIn("candidate_action_count", patched)
        self.assertEqual(EVALUATOR.read_bytes(), before)

    def test_boolean_seat_is_rejected_before_parent_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = build_artifacts(Path(directory))
            control = synthetic_report(artifacts, "control")
            candidate = synthetic_report(artifacts, "ablation")
            control["games"][0]["candidate_seat"] = True
            with self.assertRaises(compare_bound.BoundCompareError):
                compare_reports(artifacts, control, candidate)

    def test_swapped_wrapper_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = build_artifacts(Path(directory))
            control = synthetic_report(artifacts, "control")
            candidate = synthetic_report(artifacts, "ablation")
            candidate["candidate"]["sha256"] = control["candidate"]["sha256"]
            with self.assertRaises(compare_bound.BoundCompareError):
                compare_reports(artifacts, control, candidate)

    def test_whole_trace_and_cash_change_without_candidate_action_is_no_signal(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = build_artifacts(Path(directory))
            control = synthetic_report(artifacts, "control")
            candidate = synthetic_report(
                artifacts,
                "ablation",
                own_delta_by_seat={0: 5.0, 1: 5.0},
                action_changed=False,
                whole_trace_changed=True,
            )
            report = compare_reports(artifacts, control, candidate)
            self.assertEqual(report["verdict"], "NO_ACTION_SIGNAL")
            self.assertEqual(report["exit_code"], 4)
            self.assertEqual(
                report["overall"]["candidate_action_changed_cells"], 0
            )
            self.assertEqual(
                report["overall"]["whole_trace_changed_cells"], 16
            )

    def test_positive_aggregate_cannot_hide_losing_seat_subgroup(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = build_artifacts(Path(directory))
            control = synthetic_report(artifacts, "control")
            candidate = synthetic_report(
                artifacts,
                "ablation",
                own_delta_by_seat={0: 10.0, 1: -1.0},
                action_changed=True,
                whole_trace_changed=True,
            )
            report = compare_reports(artifacts, control, candidate)
            self.assertGreater(report["overall"]["mean_own_delta"], 0)
            self.assertGreaterEqual(
                report["by_opponent"]["arlene"]["mean_own_delta"], 0
            )
            self.assertEqual(
                report["by_opponent_seat"]["arlene:seat1"][
                    "mean_own_delta"
                ],
                -1.0,
            )
            self.assertEqual(report["verdict"], "MIXED")
            self.assertEqual(report["exit_code"], 1)

    def test_distinct_invocations_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = build_artifacts(Path(directory))
            control = synthetic_report(artifacts, "control")
            candidate = synthetic_report(artifacts, "ablation")
            candidate["invocation_id"] = control["invocation_id"]
            with self.assertRaises(compare_bound.BoundCompareError):
                compare_reports(artifacts, control, candidate)


if __name__ == "__main__":
    unittest.main()
