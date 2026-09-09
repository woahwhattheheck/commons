# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import unittest

import compare as target
from activation_eval import ACTION_CAPTURE_BOUNDARY, ACTION_DIGEST_SCHEMA, CORE_EVALUATOR_GIT_BLOB
from materialize import ABLATION_SCENARIOS, OPERATION, V2_SCENARIOS

HEAD = "f" * 40
SOURCE_CLOSURE = "c" * 64
CONTROL_ENTRY = "a" * 64
ABLATION_ENTRY = "b" * 64


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def receipt(arm: str):
    source_inventory = {
        "FREEZE.json": {"bytes": 1, "sha256": "5" * 64},
        "candidate.py": {"bytes": 66, "sha256": target.ENTRYPOINT_SHA256},
        "scheduler.py": {"bytes": 19483, "sha256": target.SCHEDULER_SHA256},
    }
    source_closure = target.closure_digest(source_inventory)
    materialized_inventory = copy.deepcopy(source_inventory)
    if arm == "ablation":
        materialized_inventory["scheduler.py"] = {"bytes": 19234, "sha256": "d" * 64}
    materialized_closure = target.closure_digest(materialized_inventory)
    entry = CONTROL_ENTRY if arm == "control" else ABLATION_ENTRY
    source = {
        "freeze_git_blob": target.FREEZE_GIT_BLOB,
        "scheduler_git_blob": target.SCHEDULER_GIT_BLOB,
        "scheduler_sha256": target.SCHEDULER_SHA256,
        "entrypoint_sha256": target.ENTRYPOINT_SHA256,
        "runtime_inventory": source_inventory,
        "runtime_closure_sha256": source_closure,
        "scenario_names": list(V2_SCENARIOS),
    }
    diff = "" if arm == "control" else "-future\n"
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "arm": arm,
        "checkout_head": HEAD,
        "source": source,
        "materialized": {
            "runtime_inventory": materialized_inventory,
            "runtime_closure_sha256": materialized_closure,
            "scheduler_git_blob": target.SCHEDULER_GIT_BLOB if arm == "control" else "6" * 40,
            "scheduler_sha256": materialized_inventory["scheduler.py"]["sha256"],
            "changed_paths": [] if arm == "control" else ["scheduler.py"],
            "scenario_names": list(V2_SCENARIOS if arm == "control" else ABLATION_SCENARIOS),
        },
        "entry": {
            "path": "entry.py",
            "bytes": 100,
            "sha256": entry,
            "runtime_closure_sha256": materialized_closure,
        },
        "patch": {
            "unified_diff": diff,
            "sha256": digest(diff),
        },
    }


def game(opponent: str, seed: int, seat: int, arm: str, own_delta: float, activated: bool):
    control_own = 100.0
    rival = 90.0
    own = control_own + (own_delta if arm == "ablation" else 0.0)
    scores = [own, rival] if seat == 0 else [rival, own]
    candidate_tag = f"control:{opponent}:{seed}:{seat}"
    if arm == "ablation" and activated:
        candidate_tag = f"ablation:{opponent}:{seed}:{seat}"
    candidate_digest = digest(candidate_tag)
    opponent_digest = digest(f"opponent:{arm}:{opponent}:{seed}:{seat}")
    by_seat = [candidate_digest, opponent_digest] if seat == 0 else [opponent_digest, candidate_digest]
    trace_tag = candidate_tag if activated or arm == "control" else f"control:{opponent}:{seed}:{seat}"
    return {
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "scores": scores,
        "failure": None,
        "steps": 719,
        "episode_steps": 720,
        "trace_sha256": digest(f"trace:{trace_tag}"),
        "opponent": opponent,
        "action_sha256_by_seat": by_seat,
        "candidate_action_sha256": candidate_digest,
        "action_digest_steps_by_seat": [719, 719],
        "candidate_action_digest_steps": 719,
        "action_digest_schema": ACTION_DIGEST_SCHEMA,
        "action_digest_capture": ACTION_CAPTURE_BOUNDARY,
    }


def report(arm: str, deltas=None, activated: bool = True):
    if deltas is None:
        deltas = {}
    games = []
    for opponent in target.EXPECTED_OPPONENTS:
        for seed in target.EXPECTED_SEEDS:
            for seat in (0, 1):
                delta = deltas.get((opponent, seat), 2.0)
                games.append(game(opponent, seed, seat, arm, delta, activated))
    return {
        "schema_version": 1,
        "invocation_id": ("1" if arm == "control" else "2") * 32,
        "engine_ref": target.ENGINE_REF,
        "engine_sha256": {
            "kaggriculture.py": "1" * 64,
            "kaggriculture.json": "2" * 64,
            "utils.py": "3" * 64,
        },
        "loader_sha256": "4" * 64,
        "evaluator_sha256": "5" * 64,
        "candidate": {
            "entry": "entry.py",
            "callable": "agent",
            "sha256": CONTROL_ENTRY if arm == "control" else ABLATION_ENTRY,
        },
        "opponents": {
            "arlene": {"entry": "arlene.py", "callable": "agent", "sha256": "6" * 64},
            "v1": {"entry": "candidate.py", "callable": "agent", "sha256": "7" * 64},
        },
        "seeds": list(target.EXPECTED_SEEDS),
        "agent_rng_seed": 20260909,
        "python": "3.11.synthetic",
        "platform": "linux",
        "limits": {
            "action_rpc_seconds": 1.0,
            "startup_seconds": 15.0,
            "game_seconds_between_steps": 180.0,
            "remaining_overage_time": 0,
        },
        "activation_overlay": {
            "schema_version": 1,
            "sha256": "9" * 64,
            "core_evaluator_git_blob": CORE_EVALUATOR_GIT_BLOB,
            "action_digest_schema": ACTION_DIGEST_SCHEMA,
            "action_digest_capture": ACTION_CAPTURE_BOUNDARY,
        },
        "reproducibility": {
            "checked": True,
            "same_trace_and_scores": True,
            "original_trace": "8" * 64,
            "replay_trace": "8" * 64,
        },
        "progress": {
            "state": "complete",
            "phase": "finalize",
            "planned_games": target.EXPECTED_CELLS,
            "recorded_games": target.EXPECTED_CELLS,
            "recheck_requested": True,
        },
        "games": games,
    }


class CompareTests(unittest.TestCase):
    def run_analysis(self, control=None, ablation=None, control_receipt=None, ablation_receipt=None):
        return target.analyze(
            control or report("control"),
            ablation or report("ablation"),
            control_receipt or receipt("control"),
            ablation_receipt or receipt("ablation"),
            HEAD,
        )

    def test_upside_screen_requires_bound_complete_grid(self):
        result = self.run_analysis()
        self.assertEqual("UPSIDE_SCREEN", result["verdict"])
        self.assertEqual(target.EXPECTED_CELLS, result["summary"]["candidate_action_changed_cells"])
        self.assertTrue(all(result["criteria"].values()))

    def test_no_activation_is_not_green(self):
        control = report("control", activated=False)
        ablation = report("ablation", deltas={key: 0.0 for key in []}, activated=False)
        for game_row in ablation["games"]:
            game_row["scores"] = copy.deepcopy(control["games"][ablation["games"].index(game_row)]["scores"])
        result = self.run_analysis(control=control, ablation=ablation)
        self.assertEqual("NO_ACTIVATION", result["verdict"])

    def test_bool_seat_and_partial_grid_fail_closed(self):
        bad = report("ablation")
        bad["games"][0]["candidate_seat"] = True
        with self.assertRaisesRegex(target.CompareError, "candidate seat"):
            self.run_analysis(ablation=bad)
        partial = report("ablation")
        partial["games"].pop()
        with self.assertRaisesRegex(target.CompareError, "exactly"):
            self.run_analysis(ablation=partial)

    def test_candidate_entry_must_match_materialization_receipt(self):
        bad = report("ablation")
        bad["candidate"]["sha256"] = "e" * 64
        with self.assertRaisesRegex(target.CompareError, "detached"):
            self.run_analysis(ablation=bad)

    def test_negative_opponent_seat_stratum_blocks_global_average(self):
        deltas = {("arlene", 0): -1.0, ("arlene", 1): 3.0, ("v1", 0): 3.0, ("v1", 1): 3.0}
        result = self.run_analysis(ablation=report("ablation", deltas=deltas))
        self.assertGreater(result["summary"]["mean_own_delta"], 0)
        self.assertEqual("REGRESSION", result["verdict"])
        self.assertFalse(result["criteria"]["nonnegative_own_cash_in_every_opponent_seat_stratum"])

    def test_unchanged_candidate_actions_cannot_change_scores(self):
        control = report("control", activated=False)
        ablation = report("ablation", activated=False)
        with self.assertRaisesRegex(target.CompareError, "without a candidate-action change"):
            self.run_analysis(control=control, ablation=ablation)


if __name__ == "__main__":
    unittest.main()
