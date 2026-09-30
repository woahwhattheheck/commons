# SPDX-License-Identifier: Apache-2.0
"""Synthetic exact-shape fixtures for closure-bound V2 screen tests."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import bind_execution
import compare
import materialize


HEAD = "a" * 40
CANDIDATE_BYTES = (
    b"# SPDX-License-Identifier: Apache-2.0\n"
    b"from scheduler import agent\n"
)


def _write_root(root: Path, label: str) -> None:
    root.mkdir(parents=True)
    (root / "candidate.py").write_bytes(CANDIDATE_BYTES)
    (root / "scheduler.py").write_text(
        "def agent(observation, configuration=None):\n"
        f"    return {{'arm': {label!r}}}\n",
        encoding="utf-8",
    )


def make_fixture(root: Path) -> dict[str, Any]:
    control_root = root / "control"
    candidate_root = root / "candidate"
    _write_root(control_root, "control")
    _write_root(candidate_root, "candidate")

    control_inventory = materialize.inventory(control_root)
    candidate_inventory = materialize.inventory(candidate_root)
    receipt = {
        "schema_version": 1,
        "source": {
            "scheduler_git_blob_sha1": compare.V2_SCHEDULER_BLOB,
            "closure_sha256": materialize.closure_sha256(control_inventory),
        },
        "ablation": {
            "changed_files": ["scheduler.py"],
            "scheduler_git_blob_sha1": "f" * 40,
            "closure_sha256": materialize.closure_sha256(candidate_inventory),
            "old_occurrences_before": 1,
            "old_occurrences_after": 0,
            "new_occurrences_before": 0,
            "new_occurrences_after": 1,
        },
    }

    engine_dir = root / "engine"
    engine_dir.mkdir()
    for name in bind_execution.EXPECTED_ENGINE_FILES:
        (engine_dir / name).write_text(f"{name}\n", encoding="utf-8")
    loader = root / "loader.py"
    evaluator = root / "evaluator.py"
    loader.write_text("LOADER = 1\n", encoding="utf-8")
    evaluator.write_text("EVALUATOR = 1\n", encoding="utf-8")

    opponent_dir = root / "opponents"
    opponent_dir.mkdir()
    arlene = opponent_dir / "arlene.py"
    v1 = opponent_dir / "candidate.py"
    arlene.write_text("def agent(obs, cfg=None): return {}\n", encoding="utf-8")
    v1.write_text("def agent(obs, cfg=None): return {}\n", encoding="utf-8")
    opponents = {
        "arlene": f"{arlene}::agent",
        "v1": f"{v1}::agent",
    }

    output_dir = root / "bound"
    binding = bind_execution.build_binding(
        control_root=control_root,
        candidate_root=candidate_root,
        materialization_receipt=receipt,
        engine_dir=engine_dir,
        loader=loader,
        evaluator=evaluator,
        opponents=opponents,
        output_dir=output_dir,
        git_head=HEAD,
    )
    return {
        "control_root": control_root,
        "candidate_root": candidate_root,
        "receipt": receipt,
        "engine_dir": engine_dir,
        "loader": loader,
        "evaluator": evaluator,
        "opponents": opponents,
        "output_dir": output_dir,
        "control_wrapper": output_dir / "control_bound.py",
        "candidate_wrapper": output_dir / "candidate_bound.py",
        "binding": binding,
    }


def game(
    opponent: str,
    seed: int,
    seat: int,
    own: float,
    rival: float,
    trace: str,
) -> dict[str, Any]:
    scores = [own, rival] if seat == 0 else [rival, own]
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "failure": None,
        "steps": 719,
        "episode_steps": 720,
        "scores": scores,
        "trace_sha256": trace,
        "daily_bank": [
            {"step": 23, "bank": [10.0, 10.0]},
            {"step": 718, "bank": list(scores)},
        ],
    }


def report(
    fixture: dict[str, Any],
    label: str,
    *,
    seat_deltas: dict[int, float] | None = None,
    seeds: list[int] | None = None,
    invocation: str | None = None,
    changed: bool = True,
) -> dict[str, Any]:
    binding = fixture["binding"]
    selected_seeds = list(binding["seeds"] if seeds is None else seeds)
    seat_deltas = seat_deltas or {0: 0.0, 1: 0.0}
    games = []
    for opponent in bind_execution.EXPECTED_OPPONENTS:
        for seed in selected_seeds:
            for seat in (0, 1):
                delta = seat_deltas[seat] if label == "candidate" else 0.0
                trace = (
                    ("1" * 64)
                    if label == "candidate" and changed
                    else ("0" * 64)
                )
                games.append(
                    game(
                        opponent,
                        seed,
                        seat,
                        100.0 + delta,
                        90.0,
                        trace,
                    )
                )
    return {
        "schema_version": 1,
        "invocation_id": invocation
        or (("1" if label == "control" else "2") * 32),
        "engine_ref": compare.ENGINE_REF,
        "engine_sha256": dict(binding["engine_sha256"]),
        "loader_sha256": binding["loader_sha256"],
        "evaluator_sha256": binding["evaluator_sha256"],
        "candidate": dict(binding["arms"][label]["wrapper"]),
        "opponents": dict(binding["opponents"]),
        "seeds": selected_seeds,
        "agent_rng_seed": binding["agent_rng_seed"],
        "python": binding["python"],
        "platform": binding["platform"],
        "limits": dict(binding["limits"]),
        "method": "Official interpreter synthetic contract",
        "games": games,
    }


def compare_kwargs(fixture: dict[str, Any]) -> dict[str, Any]:
    return {
        "git_head": HEAD,
        "control_root": fixture["control_root"],
        "candidate_root": fixture["candidate_root"],
        "control_wrapper": fixture["control_wrapper"],
        "candidate_wrapper": fixture["candidate_wrapper"],
        "engine_dir": fixture["engine_dir"],
        "loader": fixture["loader"],
        "evaluator": fixture["evaluator"],
        "opponents": fixture["opponents"],
    }
