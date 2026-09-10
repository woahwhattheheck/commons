# SPDX-License-Identifier: Apache-2.0
"""Verify, compare, and gate the exact current-TITAN paired action panel."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Mapping

import bind_execution
import materialize
import materialize_evaluator

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_EPISODE_STEPS = 720
EXPECTED_ACTIONS = EXPECTED_EPISODE_STEPS - 1
EXPECTED_KEYS = {
    (opponent, seed, seat)
    for opponent in bind_execution.EXPECTED_OPPONENTS
    for seed in bind_execution.EXPECTED_SEEDS
    for seat in (0, 1)
}


class ScreenError(ValueError):
    """Evidence is incomplete, detached, incomparable, or malformed."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ScreenError(f"{label} is not an object")
    return value


def _hex(value: Any, label: str, length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ScreenError(f"{label} is not lowercase {length}-hex")
    return value


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScreenError(f"{label} is not numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ScreenError(f"{label} is not finite")
    return parsed


def _file_sha256(path: Path, label: str) -> str:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ScreenError(f"{label} is not one regular file: {path}")
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ScreenError(f"cannot read {label}: {exc}") from exc


def _fingerprint_spec(spec: str, label: str) -> dict[str, str]:
    path_text, separator, callable_name = spec.partition("::")
    if separator and callable_name != "agent":
        raise ScreenError(f"{label} callable must be agent")
    path = Path(path_text).resolve()
    return {
        "entry": path.name,
        "callable": callable_name if separator else "agent",
        "sha256": _file_sha256(path, label),
    }


def _exact_limits(value: Any, label: str) -> dict[str, Any]:
    mapping = _mapping(value, label)
    expected = bind_execution.EXPECTED_LIMITS
    if set(mapping) != set(expected):
        raise ScreenError(f"{label} keys differ from exact limit contract")
    output: dict[str, Any] = {}
    for key, wanted in expected.items():
        actual = mapping.get(key)
        if (
            isinstance(actual, bool)
            or not isinstance(actual, (int, float))
            or not math.isfinite(float(actual))
            or float(actual) != float(wanted)
        ):
            raise ScreenError(f"{label}.{key} differs from {wanted!r}")
        output[key] = actual
    return output


def validate_materialization(
    receipt: Mapping[str, Any],
    *,
    control_root: Path,
    candidate_root: Path,
) -> dict[str, Any]:
    if (
        receipt.get("schema_version") != 1
        or receipt.get("operation") != materialize.OPERATION
        or receipt.get("experiment") != materialize.EXPERIMENT
    ):
        raise ScreenError("materialization identity mismatch")
    archive = _mapping(receipt.get("archive"), "archive receipt")
    source = _mapping(receipt.get("source"), "source receipt")
    candidate = _mapping(receipt.get("ablation"), "candidate receipt")
    if archive.get("sha256") != materialize.EXPECTED_ARCHIVE_SHA256:
        raise ScreenError("materialization is not bound to current canonical archive")
    if archive.get("git_blob_sha1") != materialize.EXPECTED_ARCHIVE_GIT_BLOB:
        raise ScreenError("canonical archive Git blob mismatch")
    if archive.get("bytes") != materialize.EXPECTED_ARCHIVE_BYTES:
        raise ScreenError("canonical archive byte count mismatch")
    if source.get("scheduler_git_blob_sha1") != materialize.EXPECTED_SCHEDULER_GIT_BLOB:
        raise ScreenError("control scheduler is not current canonical scheduler")
    if source.get("entry_sha256") != materialize.EXPECTED_ENTRY_SHA256:
        raise ScreenError("control entry is not current canonical main.py")
    if candidate.get("entry_sha256") != materialize.EXPECTED_ENTRY_SHA256:
        raise ScreenError("candidate main.py changed")
    if candidate.get("changed_files") != ["scheduler.py"]:
        raise ScreenError("candidate is not one-factor scheduler-only")
    if (
        candidate.get("old_occurrences_before") != 1
        or candidate.get("old_occurrences_after") != 0
        or candidate.get("new_occurrences_before") != 0
        or candidate.get("new_occurrences_after") != 1
    ):
        raise ScreenError("priority replacement cardinality is invalid")

    expected_control = _hex(source.get("closure_sha256"), "control closure", 64)
    expected_candidate = _hex(
        candidate.get("closure_sha256"), "candidate closure", 64
    )
    actual_control = materialize.closure_sha256(
        materialize.inventory(Path(control_root).resolve())
    )
    actual_candidate = materialize.closure_sha256(
        materialize.inventory(Path(candidate_root).resolve())
    )
    if actual_control != expected_control:
        raise ScreenError("control root changed after materialization")
    if actual_candidate != expected_candidate:
        raise ScreenError("candidate root changed after materialization")
    if expected_control == expected_candidate:
        raise ScreenError("control and candidate closures are equal")
    return {
        "control_closure_sha256": expected_control,
        "candidate_closure_sha256": expected_candidate,
        "control_scheduler_git_blob_sha1": source["scheduler_git_blob_sha1"],
        "candidate_scheduler_git_blob_sha1": candidate.get(
            "scheduler_git_blob_sha1"
        ),
        "archive_sha256": archive["sha256"],
        "entry_sha256": materialize.EXPECTED_ENTRY_SHA256,
    }


def validate_evaluator_materialization(
    receipt: Mapping[str, Any],
    *,
    source_evaluator: Path,
    patched_evaluator: Path,
) -> dict[str, str]:
    if (
        receipt.get("schema_version") != 1
        or receipt.get("operation") != materialize.OPERATION
        or receipt.get("experiment") != materialize.EXPERIMENT
        or receipt.get("repair") != materialize_evaluator.REPAIR
    ):
        raise ScreenError("evaluator materialization identity mismatch")
    source = _mapping(receipt.get("source"), "evaluator source")
    patched = _mapping(receipt.get("patched"), "patched evaluator")
    source_path = Path(source_evaluator)
    patched_path = Path(patched_evaluator)
    source_bytes = source_path.read_bytes()
    patched_bytes = patched_path.read_bytes()
    source_blob = materialize.git_blob_sha1(source_bytes)
    if source_blob != materialize_evaluator.EXPECTED_EVALUATOR_BLOB:
        raise ScreenError("source evaluator Git blob drift")
    if (
        source.get("git_blob_sha1") != source_blob
        or source.get("sha256") != materialize.sha256(source_bytes)
        or source.get("bytes") != len(source_bytes)
    ):
        raise ScreenError("evaluator source receipt is detached")
    if (
        patched.get("git_blob_sha1") != materialize.git_blob_sha1(patched_bytes)
        or patched.get("sha256") != materialize.sha256(patched_bytes)
        or patched.get("bytes") != len(patched_bytes)
    ):
        raise ScreenError("patched evaluator receipt is detached")
    if patched_bytes == source_bytes:
        raise ScreenError("patched evaluator equals source")
    if (
        patched.get("candidate_action_field") != "candidate_action_sha256"
        or patched.get("candidate_action_count_field") != "candidate_action_count"
        or patched.get("capture_phase")
        != "after both returned actions, before interpreter"
    ):
        raise ScreenError("candidate action capture contract mismatch")
    patches = patched.get("patches")
    if not isinstance(patches, list) or len(patches) != 3:
        raise ScreenError("evaluator patch receipt is incomplete")
    for index, row in enumerate(patches):
        row = _mapping(row, f"evaluator patch {index}")
        if (
            row.get("old_occurrences_before") != 1
            or row.get("old_occurrences_after") != 0
            or row.get("new_occurrences_after") != 1
        ):
            raise ScreenError(f"evaluator patch {index} cardinality invalid")
        _hex(row.get("old_sha256"), f"evaluator patch {index} old SHA", 64)
        _hex(row.get("new_sha256"), f"evaluator patch {index} new SHA", 64)
    return {
        "source_git_blob_sha1": source_blob,
        "source_sha256": materialize.sha256(source_bytes),
        "patched_git_blob_sha1": materialize.git_blob_sha1(patched_bytes),
        "patched_sha256": materialize.sha256(patched_bytes),
    }


def validate_binding(
    binding: Mapping[str, Any],
    materialization_receipt: Mapping[str, Any],
    *,
    git_head: str,
    control_root: Path,
    candidate_root: Path,
    control_wrapper: Path,
    candidate_wrapper: Path,
    engine_dir: Path,
    loader: Path,
    evaluator: Path,
    opponents: Mapping[str, str],
) -> dict[str, Any]:
    git_head = _hex(git_head, "git head", 40)
    if (
        binding.get("schema_version") != 1
        or binding.get("operation") != bind_execution.OPERATION
        or binding.get("experiment") != materialize.EXPERIMENT
        or binding.get("git_head") != git_head
    ):
        raise ScreenError("execution binding identity mismatch")
    closure = validate_materialization(
        materialization_receipt,
        control_root=control_root,
        candidate_root=candidate_root,
    )
    if binding.get("seeds") != list(bind_execution.EXPECTED_SEEDS):
        raise ScreenError("execution binding seed grid mismatch")
    if binding.get("agent_rng_seed") != bind_execution.EXPECTED_AGENT_RNG_SEED:
        raise ScreenError("execution binding RNG seed mismatch")
    limits = _exact_limits(binding.get("limits"), "execution binding limits")
    if binding.get("python") != sys.version or binding.get("platform") != sys.platform:
        raise ScreenError("execution binding runtime identity drift")

    arms = _mapping(binding.get("arms"), "execution binding arms")
    if set(arms) != {"control", "candidate"}:
        raise ScreenError("execution binding arm set mismatch")
    roots = {
        "control": Path(control_root).resolve(),
        "candidate": Path(candidate_root).resolve(),
    }
    wrappers = {
        "control": Path(control_wrapper).resolve(),
        "candidate": Path(candidate_wrapper).resolve(),
    }
    expected_closures = {
        "control": closure["control_closure_sha256"],
        "candidate": closure["candidate_closure_sha256"],
    }
    checked_arms: dict[str, Any] = {}
    for label in ("control", "candidate"):
        arm = _mapping(arms.get(label), f"{label} arm")
        if arm.get("closure_sha256") != expected_closures[label]:
            raise ScreenError(f"{label} arm closure is detached")
        if (
            arm.get("entry_sha256") != materialize.EXPECTED_ENTRY_SHA256
            or arm.get("entrypoint") != materialize.EXPECTED_ENTRYPOINT
        ):
            raise ScreenError(f"{label} entry identity mismatch")
        if (
            _file_sha256(roots[label] / "main.py", f"{label} main.py")
            != materialize.EXPECTED_ENTRY_SHA256
        ):
            raise ScreenError(f"{label} main.py changed")
        wrapper = {
            "entry": wrappers[label].name,
            "callable": "agent",
            "sha256": _file_sha256(wrappers[label], f"{label} wrapper"),
        }
        if dict(_mapping(arm.get("wrapper"), f"{label} wrapper receipt")) != wrapper:
            raise ScreenError(f"{label} wrapper receipt is detached")
        checked_arms[label] = {
            "closure_sha256": expected_closures[label],
            "entry_sha256": materialize.EXPECTED_ENTRY_SHA256,
            "entrypoint": materialize.EXPECTED_ENTRYPOINT,
            "wrapper": wrapper,
        }
    if checked_arms["control"]["wrapper"]["sha256"] == checked_arms["candidate"]["wrapper"]["sha256"]:
        raise ScreenError("control and candidate wrapper identities are equal")

    engine_dir = Path(engine_dir).resolve()
    engine = {
        name: _file_sha256(engine_dir / name, f"engine {name}")
        for name in bind_execution.EXPECTED_ENGINE_FILES
    }
    if dict(_mapping(binding.get("engine_sha256"), "engine hashes")) != engine:
        raise ScreenError("execution binding engine bytes changed")
    loader_sha = _file_sha256(Path(loader).resolve(), "loader")
    evaluator_sha = _file_sha256(Path(evaluator).resolve(), "evaluator")
    if binding.get("loader_sha256") != loader_sha:
        raise ScreenError("execution binding loader bytes changed")
    if binding.get("evaluator_sha256") != evaluator_sha:
        raise ScreenError("execution binding evaluator bytes changed")

    if tuple(sorted(opponents)) != tuple(sorted(bind_execution.EXPECTED_OPPONENTS)):
        raise ScreenError("classification opponent bank mismatch")
    actual_opponents = {
        name: _fingerprint_spec(opponents[name], f"opponent {name}")
        for name in bind_execution.EXPECTED_OPPONENTS
    }
    if dict(_mapping(binding.get("opponents"), "opponent fingerprints")) != actual_opponents:
        raise ScreenError("execution binding opponent bytes changed")
    return {
        "git_head": git_head,
        "closure": closure,
        "arms": checked_arms,
        "engine_sha256": engine,
        "loader_sha256": loader_sha,
        "evaluator_sha256": evaluator_sha,
        "opponents": actual_opponents,
        "seeds": list(bind_execution.EXPECTED_SEEDS),
        "agent_rng_seed": bind_execution.EXPECTED_AGENT_RNG_SEED,
        "limits": limits,
        "python": binding["python"],
        "platform": binding["platform"],
    }


def _daily_map(game: Mapping[str, Any], label: str) -> dict[int, tuple[float, float]]:
    rows = game.get("daily_bank")
    if not isinstance(rows, list) or not rows:
        raise ScreenError(f"{label} daily_bank is empty or invalid")
    output: dict[int, tuple[float, float]] = {}
    for index, row in enumerate(rows):
        row = _mapping(row, f"{label} daily row {index}")
        step = row.get("step")
        bank = row.get("bank")
        if (
            type(step) is not int
            or step in output
            or not isinstance(bank, list)
            or len(bank) != 2
        ):
            raise ScreenError(f"{label} daily row {index} identity invalid")
        output[step] = (
            _number(bank[0], f"{label} daily bank 0"),
            _number(bank[1], f"{label} daily bank 1"),
        )
    return output


def validate_report(
    report: Mapping[str, Any],
    *,
    label: str,
    binding: Mapping[str, Any],
) -> tuple[str, dict[tuple[str, int, int], dict[str, Any]]]:
    if report.get("schema_version") != 1:
        raise ScreenError(f"{label} report schema mismatch")
    if report.get("engine_ref") != ENGINE_REF:
        raise ScreenError(f"{label} engine ref mismatch")
    invocation = _hex(report.get("invocation_id"), f"{label} invocation", 32)
    expected_candidate = binding["arms"][label]["wrapper"]
    if dict(_mapping(report.get("candidate"), f"{label} candidate")) != expected_candidate:
        raise ScreenError(f"{label} candidate wrapper identity mismatch")
    if report.get("engine_sha256") != binding["engine_sha256"]:
        raise ScreenError(f"{label} engine identity mismatch")
    if report.get("loader_sha256") != binding["loader_sha256"]:
        raise ScreenError(f"{label} loader identity mismatch")
    if report.get("evaluator_sha256") != binding["evaluator_sha256"]:
        raise ScreenError(f"{label} evaluator identity mismatch")
    if report.get("opponents") != binding["opponents"]:
        raise ScreenError(f"{label} opponents mismatch")
    if report.get("seeds") != binding["seeds"]:
        raise ScreenError(f"{label} seeds mismatch")
    if report.get("agent_rng_seed") != binding["agent_rng_seed"]:
        raise ScreenError(f"{label} RNG seed mismatch")
    _exact_limits(report.get("limits"), f"{label} limits")
    if report.get("python") != binding["python"] or report.get("platform") != binding["platform"]:
        raise ScreenError(f"{label} runtime identity mismatch")
    method = report.get("method")
    if not isinstance(method, str) or not method:
        raise ScreenError(f"{label} method missing")

    games = report.get("games")
    if not isinstance(games, list) or len(games) != len(EXPECTED_KEYS):
        raise ScreenError(f"{label} must contain exactly {len(EXPECTED_KEYS)} games")
    grid: dict[tuple[str, int, int], dict[str, Any]] = {}
    for index, raw in enumerate(games):
        game = _mapping(raw, f"{label} game {index}")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        key = (opponent, seed, seat)
        if key not in EXPECTED_KEYS or key in grid:
            raise ScreenError(f"{label} invalid or duplicate game key {key!r}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise ScreenError(f"{label} incomplete game {key}: {game.get('failure')}")
        if (
            game.get("episode_steps") != EXPECTED_EPISODE_STEPS
            or game.get("steps") != EXPECTED_ACTIONS
            or game.get("candidate_action_count") != EXPECTED_ACTIONS
        ):
            raise ScreenError(f"{label} incomplete action coverage for {key}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise ScreenError(f"{label} score vector invalid for {key}")
        copied = dict(game)
        copied["scores"] = [
            _number(scores[0], f"{label} {key} score 0"),
            _number(scores[1], f"{label} {key} score 1"),
        ]
        copied["candidate_action_sha256"] = _hex(
            game.get("candidate_action_sha256"),
            f"{label} {key} candidate actions",
            64,
        )
        copied["trace_sha256"] = _hex(
            game.get("trace_sha256"), f"{label} {key} whole trace", 64
        )
        copied["_daily"] = _daily_map(game, f"{label} {key}")
        grid[key] = copied
    if set(grid) != EXPECTED_KEYS:
        raise ScreenError(f"{label} paired grid is incomplete")
    return invocation, grid


def _outcome(own: float, rival: float) -> str:
    if own > rival:
        return "win"
    if own < rival:
        return "loss"
    return "tie"


def _first_daily_divergence(
    left: Mapping[int, tuple[float, float]],
    right: Mapping[int, tuple[float, float]],
) -> int | None:
    if set(left) != set(right):
        raise ScreenError("control/candidate daily checkpoint grids differ")
    for step in sorted(left):
        if left[step] != right[step]:
            return step
    return None


def assess_rows(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    if len(rows) != len(EXPECTED_KEYS):
        raise ScreenError(f"expected {len(EXPECTED_KEYS)} paired rows")
    own_deltas = [_number(row.get("own_delta"), "own delta") for row in rows]
    margin_deltas = [
        _number(row.get("margin_delta"), "margin delta") for row in rows
    ]
    changed_cells = sum(bool(row.get("candidate_action_changed")) for row in rows)
    transitions: dict[str, int] = defaultdict(int)
    new_losses: list[Mapping[str, Any]] = []
    lost_wins: list[Mapping[str, Any]] = []
    grouped: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        opponent = row.get("opponent")
        seat = row.get("seat")
        if opponent not in bind_execution.EXPECTED_OPPONENTS or seat not in (0, 1):
            raise ScreenError("row opponent/seat invalid")
        before = str(row.get("control_outcome"))
        after = str(row.get("candidate_outcome"))
        if before not in ("win", "loss", "tie") or after not in ("win", "loss", "tie"):
            raise ScreenError("row outcome invalid")
        transitions[f"{before}->{after}"] += 1
        if before != "loss" and after == "loss":
            new_losses.append(row)
        if before == "win" and after != "win":
            lost_wins.append(row)
        grouped[(str(opponent), int(seat))].append(row)

    strata: dict[str, dict[str, Any]] = {}
    for (opponent, seat), values in sorted(grouped.items()):
        own = [_number(row.get("own_delta"), "stratum own delta") for row in values]
        margin = [
            _number(row.get("margin_delta"), "stratum margin delta")
            for row in values
        ]
        stratum_new_losses = sum(
            row.get("control_outcome") != "loss"
            and row.get("candidate_outcome") == "loss"
            for row in values
        )
        strata[f"{opponent}:seat-{seat}"] = {
            "opponent": opponent,
            "seat": seat,
            "cells": len(values),
            "candidate_action_changed_cells": sum(
                bool(row.get("candidate_action_changed")) for row in values
            ),
            "positive_cells": sum(delta > 0 for delta in own),
            "zero_cells": sum(delta == 0 for delta in own),
            "negative_cells": sum(delta < 0 for delta in own),
            "mean_own_delta": statistics.mean(own),
            "median_own_delta": statistics.median(own),
            "mean_margin_delta": statistics.mean(margin),
            "new_losses": stratum_new_losses,
        }
    expected_strata = {
        f"{opponent}:seat-{seat}"
        for opponent in bind_execution.EXPECTED_OPPONENTS
        for seat in (0, 1)
    }
    if set(strata) != expected_strata:
        raise ScreenError("opponent-by-seat strata are incomplete")

    overall = {
        "cells": len(rows),
        "candidate_action_changed_cells": changed_cells,
        "positive_cells": sum(delta > 0 for delta in own_deltas),
        "zero_cells": sum(delta == 0 for delta in own_deltas),
        "negative_cells": sum(delta < 0 for delta in own_deltas),
        "mean_own_delta": statistics.mean(own_deltas),
        "median_own_delta": statistics.median(own_deltas),
        "minimum_own_delta": min(own_deltas),
        "maximum_own_delta": max(own_deltas),
        "mean_margin_delta": statistics.mean(margin_deltas),
        "new_losses": len(new_losses),
        "lost_wins": len(lost_wins),
    }
    underlying_upside = (
        changed_cells > 0
        and overall["mean_own_delta"] > 0
        and overall["median_own_delta"] >= 0
        and overall["positive_cells"] >= overall["negative_cells"]
        and all(
            value["mean_own_delta"] >= 0
            for value in strata.values()
        )
    )
    gates = {
        "underlying_upside_screen": underlying_upside,
        "candidate_action_activation": changed_cells > 0,
        "positive_mean_own_cash": overall["mean_own_delta"] > 0,
        "nonnegative_median_own_cash": overall["median_own_delta"] >= 0,
        "nonnegative_cell_balance": (
            overall["positive_cells"] >= overall["negative_cells"]
        ),
        "positive_mean_margin": overall["mean_margin_delta"] > 0,
        "zero_new_losses": not new_losses,
        "all_opponent_seat_strata_nonnegative": all(
            value["mean_own_delta"] >= 0
            and value["median_own_delta"] >= 0
            and value["positive_cells"] >= value["negative_cells"]
            and value["mean_margin_delta"] >= 0
            and value["new_losses"] == 0
            for value in strata.values()
        ),
    }
    failed = [name for name, passed in gates.items() if not passed]
    return {
        "verdict": "ADMIT" if not failed else "REJECT",
        "reason": (
            "all current-port win-oriented gates passed"
            if not failed
            else "failed gates: " + ", ".join(failed)
        ),
        "exit_code": 0 if not failed else 1,
        "underlying_verdict": "UPSIDE_SCREEN" if underlying_upside else "NO_UPSIDE_SCREEN",
        "gates": gates,
        "overall": overall,
        "outcome_transitions": dict(sorted(transitions.items())),
        "by_opponent_seat": strata,
        "new_loss_rows": list(new_losses),
        "lost_win_rows": list(lost_wins),
    }


def compare_and_assess(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    materialization_receipt: Mapping[str, Any],
    execution_binding: Mapping[str, Any],
    evaluator_receipt: Mapping[str, Any],
    *,
    source_evaluator: Path,
    git_head: str,
    control_root: Path,
    candidate_root: Path,
    control_wrapper: Path,
    candidate_wrapper: Path,
    engine_dir: Path,
    loader: Path,
    evaluator: Path,
    opponents: Mapping[str, str],
) -> dict[str, Any]:
    binding = validate_binding(
        execution_binding,
        materialization_receipt,
        git_head=git_head,
        control_root=control_root,
        candidate_root=candidate_root,
        control_wrapper=control_wrapper,
        candidate_wrapper=candidate_wrapper,
        engine_dir=engine_dir,
        loader=loader,
        evaluator=evaluator,
        opponents=opponents,
    )
    evaluator_binding = validate_evaluator_materialization(
        evaluator_receipt,
        source_evaluator=source_evaluator,
        patched_evaluator=evaluator,
    )
    control_invocation, left = validate_report(
        control, label="control", binding=binding
    )
    candidate_invocation, right = validate_report(
        candidate, label="candidate", binding=binding
    )
    if control_invocation == candidate_invocation:
        raise ScreenError("control and candidate invocation IDs are equal")
    if control.get("method") != candidate.get("method"):
        raise ScreenError("control/candidate evaluation method drift")
    if set(left) != set(right):
        raise ScreenError("paired game grids differ")

    rows: list[dict[str, Any]] = []
    for key in sorted(left):
        opponent, seed, seat = key
        baseline = left[key]
        ablation = right[key]
        control_own = baseline["scores"][seat]
        control_rival = baseline["scores"][1 - seat]
        candidate_own = ablation["scores"][seat]
        candidate_rival = ablation["scores"][1 - seat]
        rows.append(
            {
                "opponent": opponent,
                "seed": seed,
                "seat": seat,
                "control_own": control_own,
                "control_rival": control_rival,
                "candidate_own": candidate_own,
                "candidate_rival": candidate_rival,
                "own_delta": candidate_own - control_own,
                "rival_delta": candidate_rival - control_rival,
                "margin_delta": (
                    candidate_own
                    - candidate_rival
                    - (control_own - control_rival)
                ),
                "control_outcome": _outcome(control_own, control_rival),
                "candidate_outcome": _outcome(candidate_own, candidate_rival),
                "candidate_action_changed": (
                    baseline["candidate_action_sha256"]
                    != ablation["candidate_action_sha256"]
                ),
                "whole_trace_changed": (
                    baseline["trace_sha256"] != ablation["trace_sha256"]
                ),
                "first_daily_bank_divergence_step": _first_daily_divergence(
                    baseline["_daily"], ablation["_daily"]
                ),
            }
        )
    assessed = assess_rows(rows)
    return {
        "schema_version": 1,
        "operation": materialize.OPERATION,
        "experiment": materialize.EXPERIMENT,
        "git_head": git_head,
        **assessed,
        "materialization_binding": binding["closure"],
        "execution_binding": binding,
        "activation_binding": {
            **evaluator_binding,
            "field": "candidate_action_sha256",
            "count_field": "candidate_action_count",
            "capture_phase": "after both returned actions, before interpreter",
            "expected_episode_steps": EXPECTED_EPISODE_STEPS,
            "expected_candidate_actions": EXPECTED_ACTIONS,
            "whole_trace_field": "trace_sha256",
            "whole_trace_is_activation": False,
        },
        "invocations": {
            "control": control_invocation,
            "candidate": candidate_invocation,
        },
        "rows": rows,
    }


def markdown(result: Mapping[str, Any]) -> str:
    lines = [
        "# TITAN V3 current-port all-shed priority screen",
        "",
        f"**Verdict:** `{result['verdict']}` — {result['reason']}",
        "",
    ]
    overall = result.get("overall")
    if isinstance(overall, Mapping):
        lines.extend(
            [
                f"- Complete paired cells: {overall['cells']}",
                (
                    "- Candidate-action-changed cells: "
                    f"{overall['candidate_action_changed_cells']}"
                ),
                (
                    "- Mean / median own-cash delta: "
                    f"{overall['mean_own_delta']:+.3f} / "
                    f"{overall['median_own_delta']:+.3f}"
                ),
                f"- Mean margin delta: {overall['mean_margin_delta']:+.3f}",
                (
                    "- Positive / zero / negative own cells: "
                    f"{overall['positive_cells']} / {overall['zero_cells']} / "
                    f"{overall['negative_cells']}"
                ),
                (
                    "- New losses / lost wins: "
                    f"{overall['new_losses']} / {overall['lost_wins']}"
                ),
                "",
                "## Admission gates",
                "",
            ]
        )
        for name, passed in result["gates"].items():
            lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")
        lines.extend(
            [
                "",
                "## Opponent × seat strata",
                "",
                (
                    "| Stratum | Cells | Changed | + / 0 / - | Mean own Δ | "
                    "Median own Δ | Mean margin Δ | New losses |"
                ),
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for name, value in result["by_opponent_seat"].items():
            lines.append(
                f"| {name} | {value['cells']} | "
                f"{value['candidate_action_changed_cells']} | "
                f"{value['positive_cells']} / {value['zero_cells']} / "
                f"{value['negative_cells']} | "
                f"{value['mean_own_delta']:+.3f} | "
                f"{value['median_own_delta']:+.3f} | "
                f"{value['mean_margin_delta']:+.3f} | "
                f"{value['new_losses']} |"
            )
        lines.extend(["", "## Outcome transitions", ""])
        for transition, count in result["outcome_transitions"].items():
            lines.append(f"- `{transition}`: {count}")
    lines.extend(
        [
            "",
            (
                "This is an exact offline current-canonical causal screen. It is "
                "not a hosted leaderboard result or submission authorization."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--materialization", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--control-wrapper", type=Path, required=True)
    parser.add_argument("--candidate-wrapper", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--evaluator-source", type=Path, required=True)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--opponent", action="append", default=[])
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = compare_and_assess(
            bind_execution.strict_object(args.control),
            bind_execution.strict_object(args.candidate),
            bind_execution.strict_object(args.materialization),
            bind_execution.strict_object(args.binding),
            bind_execution.strict_object(args.evaluator_receipt),
            source_evaluator=args.evaluator_source,
            git_head=args.head,
            control_root=args.control_root,
            candidate_root=args.candidate_root,
            control_wrapper=args.control_wrapper,
            candidate_wrapper=args.candidate_wrapper,
            engine_dir=args.engine_dir,
            loader=args.loader,
            evaluator=args.evaluator,
            opponents=bind_execution._parse_opponents(args.opponent),
        )
    except (
        ScreenError,
        bind_execution.BindingError,
        materialize.MaterializeError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        result = {
            "schema_version": 1,
            "operation": materialize.OPERATION,
            "experiment": materialize.EXPERIMENT,
            "git_head": args.head,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
        }

    materialize.atomic_write(
        args.output,
        (
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode("utf-8"),
    )
    materialize.atomic_write(args.markdown, markdown(result).encode("utf-8"))
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "reason": result["reason"],
                "exit_code": result["exit_code"],
                "overall": result.get("overall"),
                "gates": result.get("gates"),
                "by_opponent_seat": result.get("by_opponent_seat"),
            },
            sort_keys=True,
        )
    )
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
