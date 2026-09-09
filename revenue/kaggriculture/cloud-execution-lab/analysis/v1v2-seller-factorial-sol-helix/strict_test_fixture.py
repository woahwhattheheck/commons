# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

import strict_factorial as strict

HEAD = "b" * 40
SHARED = {
    "evaluator_source_sha256": "1" * 64,
    "loader_sha256": "2" * 64,
    "opponent_entry_sha256": {
        "arlene": "3" * 64,
        "apex": "4" * 64,
        "public_bt12": "5" * 64,
        "v1": "6" * 64,
    },
    "opponent_bundles": {
        name: {"root": name, "files": 1, "sha256": hashlib.sha256(name.encode()).hexdigest()}
        for name in strict.EXPECTED_OPPONENTS
    },
    "generated_apex_binary": {"sha256": "7" * 64, "bytes": 42},
}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=False, allow_nan=False) + "\n", encoding="utf-8")


class Fixture:
    def __init__(self, root: Path, *, deltas: Mapping[str, Any] | None = None,
                 rival_deltas: Mapping[str, Any] | None = None,
                 action_same: frozenset[str] = frozenset()) -> None:
        self.root = root
        self.paths: dict[str, Path] = {}
        self.deltas = dict(deltas or {
            "control": 0.0,
            "carry_095": 10.0,
            "force_end": 5.0,
            "both": 25.0,
        })
        self.rival_deltas = dict(rival_deltas or {arm: 0.0 for arm in strict.ARMS})
        self.action_same = action_same
        self._build()

    def _delta(self, arm: str, seat: int) -> float:
        value = self.deltas[arm]
        if isinstance(value, Mapping):
            return float(value[seat])
        return float(value)

    def _rival_delta(self, arm: str, seat: int) -> float:
        value = self.rival_deltas[arm]
        if isinstance(value, Mapping):
            return float(value[seat])
        return float(value)

    def _bundle(self, arm: str) -> tuple[Path, dict[str, Any]]:
        bundle = self.root / "arms" / arm
        bundle.mkdir(parents=True)
        (bundle / "scheduler.py").write_text(
            "def agent(observation, configuration=None):\n"
            f"    return {{'market': [], 'arm': {arm!r}}}\n",
            encoding="utf-8",
        )
        (bundle / "candidate.py").write_text(
            "from scheduler import agent\n", encoding="utf-8"
        )
        carry, force = strict.EXPECTED_INTERVENTIONS[arm]
        arm_record = {
            "schema_version": 1,
            "operation": strict.OPERATION,
            "arm": arm,
            "frozen_source": {
                "variant": "v2",
                "scheduler_sha256": "72865b83e66d0c1ed27ddc35e5ab428f8212872e8e8e918f2826eb7665fbe7f8",
                "scheduler_git_blob": "7c068b7078c3d7c09bb3836590ad42b0af934cdf",
            },
            "interventions": {
                "carry_discount": carry,
                "force_residual_reference_at_horizon": force,
            },
            "scheduler_sha256": strict.sha256_file(bundle / "scheduler.py"),
        }
        _write_json(bundle / "ARM.json", arm_record)
        closure = strict.tree_receipt(bundle, exclude=frozenset({"bound_entry.py"}))
        entry = bundle / "bound_entry.py"
        entry.write_text(strict.bound_entry_source(closure, arm), encoding="utf-8")
        final_bundle = strict.tree_receipt(bundle)
        receipt = {
            "schema_version": 1,
            "operation": strict.OPERATION,
            "arm": arm,
            "source": {
                "variant": "v2",
                "scheduler_sha256": "72865b83e66d0c1ed27ddc35e5ab428f8212872e8e8e918f2826eb7665fbe7f8",
                "scheduler_git_blob": "7c068b7078c3d7c09bb3836590ad42b0af934cdf",
            },
            "patch": {
                "arm": arm,
                "carry_discount": carry,
                "force_residual_reference_at_horizon": force,
            },
            "closure_bound_at_entry": closure,
            "entrypoint": {
                "relative_path": "bound_entry.py",
                "sha256": strict.sha256_file(entry),
                "import_ownership": "candidate+scheduler-under-bound-root-v1",
            },
            "materialized_bundle": final_bundle,
        }
        evidence = self.root / "evidence" / arm
        receipt_path = evidence / "MATERIALIZATION.json"
        _write_json(receipt_path, receipt)
        return bundle, receipt

    def _game(self, arm: str, opponent: str, seed: int, seat: int) -> dict[str, Any]:
        own = 100.0 + self._delta(arm, seat)
        rival = 80.0 + self._rival_delta(arm, seat)
        scores = [own, rival] if seat == 0 else [rival, own]
        action_arm = "control" if arm in self.action_same else arm
        return {
            "opponent": opponent,
            "seed": seed,
            "candidate_seat": seat,
            "status": "complete",
            "failure": None,
            "scores": scores,
            "steps": strict.EXPECTED_STEPS,
            "episode_steps": strict.EXPECTED_EPISODE_STEPS,
            "candidate_action_count": strict.EXPECTED_ACTION_COUNT,
            "candidate_action_sha256": _digest(f"action:{action_arm}:{opponent}:{seed}:{seat}"),
            "trace_sha256": _digest(f"trace:{arm}:{opponent}:{seed}:{seat}"),
            "actors": [
                {"calls": strict.EXPECTED_ACTION_COUNT},
                {"calls": strict.EXPECTED_ACTION_COUNT},
            ],
        }

    def _raw(self, arm: str, shard: int, seeds: list[int], identity: Mapping[str, Any],
             games: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "invocation_id": hashlib.md5(f"{arm}:{shard}".encode()).hexdigest(),
            "engine_ref": strict.EXPECTED_ENGINE_REF,
            "engine_sha256": {name: _digest("engine:" + name) for name in strict.EXPECTED_ENGINE_FILES},
            "loader_sha256": identity["loader_sha256"],
            "evaluator_sha256": identity["evaluator_effective_sha256"],
            "candidate": {"entry": "bound_entry.py", "callable": "agent", "sha256": identity["entry_sha256"]},
            "opponents": {
                name: {"entry": f"{name}.py", "callable": "agent", "sha256": identity["opponent_entry_sha256"][name]}
                for name in strict.EXPECTED_OPPONENTS
            },
            "seeds": seeds,
            "agent_rng_seed": strict.EXPECTED_AGENT_RNG_SEED,
            "python": "3.11.9 (synthetic strict contract)",
            "platform": "linux",
            "limits": dict(strict.EXPECTED_LIMITS),
            "method": strict.EXPECTED_METHOD,
            "games": games,
            "progress": {
                "state": "complete",
                "phase": "finalize",
                "planned_games": len(games),
                "recorded_games": len(games),
                "active_game": None,
                "recheck_requested": False,
            },
        }

    def _build(self) -> None:
        effective_bytes = b"# patched evaluator with candidate-only action digest\n"
        effective_sha = strict.sha256_bytes(effective_bytes)
        effective_blob = strict.git_blob_sha1(effective_bytes)
        for arm in strict.ARMS:
            bundle, receipt = self._bundle(arm)
            evidence = self.root / "evidence" / arm
            shard_dir = evidence / f"{arm}-shards"
            shard_dir.mkdir(parents=True)
            evaluator_name = "evaluate-sol-vector.py"
            (shard_dir / evaluator_name).write_bytes(effective_bytes)
            evaluator_receipt = {
                "schema_version": 1,
                "operation": "titan-v2-target-domain-ablation-20260909-sol-bulwark-01",
                "repair": "sol-candidate-action-evidence-v1",
                "source": {
                    "path_name": "evaluate.py",
                    "git_blob_sha1": strict.EXPECTED_EVALUATOR_SOURCE_BLOB,
                    "sha256": SHARED["evaluator_source_sha256"],
                    "bytes": 1,
                },
                "patched": {
                    "path_name": evaluator_name,
                    "git_blob_sha1": effective_blob,
                    "sha256": effective_sha,
                    "bytes": len(effective_bytes),
                    "candidate_action_field": "candidate_action_sha256",
                    "candidate_action_count_field": "candidate_action_count",
                    "capture_phase": "after both returned actions, before interpreter",
                    "patches": [
                        {
                            "label": label,
                            "old_sha256": _digest("old:" + label),
                            "new_sha256": _digest("new:" + label),
                            "old_occurrences_before": 1,
                            "old_occurrences_after": 0,
                            "old_occurrences_after_raw": strict.EXPECTED_EVALUATOR_RAW_OLD_AFTER[index],
                            "old_occurrences_embedded_in_replacement": strict.EXPECTED_EVALUATOR_EMBEDDED_OLD[index],
                            "new_occurrences_after": 1,
                        }
                        for index, label in enumerate((
                            "candidate digest initialization",
                            "pre-interpreter candidate action capture",
                            "candidate digest publication",
                        ))
                    ],
                },
            }
            _write_json(shard_dir / "EVALUATOR-MATERIALIZATION.json", evaluator_receipt)
            identity = {
                "operation": strict.OPERATION,
                "git_head": HEAD,
                "arm": arm,
                "entrypoint": str(bundle / "bound_entry.py"),
                "entry_sha256": strict.sha256_file(bundle / "bound_entry.py"),
                "closure": receipt["closure_bound_at_entry"],
                "materialization_receipt_sha256": strict.sha256_file(evidence / "MATERIALIZATION.json"),
                "evaluator_source_sha256": SHARED["evaluator_source_sha256"],
                "evaluator_effective_sha256": effective_sha,
                "loader_sha256": SHARED["loader_sha256"],
                "engine_ref": strict.EXPECTED_ENGINE_REF,
                "opponent_entry_sha256": SHARED["opponent_entry_sha256"],
                "opponent_bundles": SHARED["opponent_bundles"],
                "generated_apex_binary": SHARED["generated_apex_binary"],
            }
            all_games: list[dict[str, Any]] = []
            groups = [
                [strict.EXPECTED_SEEDS[0], strict.EXPECTED_SEEDS[2]],
                [strict.EXPECTED_SEEDS[1], strict.EXPECTED_SEEDS[3]],
            ]
            for shard, seeds in enumerate(groups):
                games = [
                    self._game(arm, opponent, seed, seat)
                    for opponent in strict.EXPECTED_OPPONENTS
                    for seed in seeds
                    for seat in (0, 1)
                ]
                all_games.extend(games)
                _write_json(
                    shard_dir / f"{arm}-shard-{shard:02d}.json",
                    self._raw(arm, shard, seeds, identity, games),
                )
            report = {
                "schema_version": 1,
                "operation": strict.OPERATION,
                "status": "complete",
                "phase": "development",
                "arm": arm,
                "identity": identity,
                "seeds": list(strict.EXPECTED_SEEDS),
                "opponents": list(strict.EXPECTED_OPPONENTS),
                "expected_cells": strict.EXPECTED_CELLS_PER_ARM,
                "completed_shards": [
                    {"shard": 0, "seeds": list(groups[0]), "returncode": 0},
                    {"shard": 1, "seeds": list(groups[1]), "returncode": 0},
                ],
                "gate": {
                    "valid": True,
                    "errors": [],
                    "accepted": strict.EXPECTED_CELLS_PER_ARM,
                    "expected": strict.EXPECTED_CELLS_PER_ARM,
                },
                "games": all_games,
            }
            report_path = evidence / "ARM.json"
            _write_json(report_path, report)
            self.paths[arm] = report_path

    def report(self, arm: str) -> dict[str, Any]:
        return json.loads(self.paths[arm].read_text(encoding="utf-8"))

    def write_report(self, arm: str, value: Mapping[str, Any]) -> None:
        _write_json(self.paths[arm], value)

    def shard_path(self, arm: str, shard: int = 0) -> Path:
        return self.root / "evidence" / arm / f"{arm}-shards" / f"{arm}-shard-{shard:02d}.json"
