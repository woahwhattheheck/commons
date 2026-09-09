# SPDX-License-Identifier: Apache-2.0
"""Admit only closure-bound, exact-grid forced-feasibility ablation evidence."""
from __future__ import annotations

import argparse
import copy
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import statistics
import sys
import tempfile
from typing import Any, Mapping

import compare as parent

OPERATION = parent.OPERATION
EXPECTED_SEEDS = (
    539131249,
    1834999074,
    2609097301,
    2611092207,
)
EXPECTED_OPPONENTS = ("arlene", "v1")
EXPECTED_EPISODE_STEPS = 720
EXPECTED_ACTION_COUNT = EXPECTED_EPISODE_STEPS - 1
EXPECTED_RNG_SEED = 20260909
EXPECTED_ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_ENGINE_FILES = (
    "kaggriculture.py",
    "kaggriculture.json",
    "utils.py",
)
EXPECTED_ENTRY_SHA256 = (
    "2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2"
)
EXPECTED_BINDING_REPAIR = "sol-keel-bound-arm-entrypoints-v1"
EXPECTED_EVALUATOR_REPAIR = "sol-keel-candidate-action-digest-v1"
EXPECTED_EVALUATOR_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
EXPECTED_LIMITS = {
    "action_rpc_seconds": 1.0,
    "startup_seconds": 15.0,
    "game_seconds_between_steps": 180.0,
    "remaining_overage_time": 0.0,
}
EXPECTED_METHOD = (
    "Official interpreter with explicit driver; not hosted Kaggle scoring. "
    "Decision timings are child-reported; RPC deadlines are parent-enforced. "
    "Resource samples combine child rusage, available Linux procfs, and final "
    "wait4 usage when supported; actor provenance records the actual sources. "
    "Entry-file hashes do not cover arbitrary agent dependencies."
)


class BoundCompareError(parent.CompareError):
    """The report is incomplete, aliased, stale, or detached from executed bytes."""


def strict_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BoundCompareError(f"{label} is not an object")
    return value


def strict_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BoundCompareError(f"{label} is not an integer")
    return value


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BoundCompareError(f"{label} is not numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise BoundCompareError(f"{label} is not finite")
    return parsed


def digest(value: Any, label: str, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise BoundCompareError(f"{label} is not a lowercase hex digest")
    return value


def file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as exc:
        raise BoundCompareError(f"cannot hash {path}: {exc}") from exc


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def inventory(root: Path) -> dict[str, dict[str, Any]]:
    root = Path(root)
    if not root.is_dir():
        raise BoundCompareError(f"payload root is not a directory: {root}")
    result: dict[str, dict[str, Any]] = {}
    try:
        paths = sorted(root.rglob("*"))
    except OSError as exc:
        raise BoundCompareError(f"cannot enumerate payload {root}: {exc}") from exc
    for path in paths:
        relative = path.relative_to(root).as_posix()
        try:
            info = path.lstat()
        except OSError as exc:
            raise BoundCompareError(f"cannot stat payload member {relative}: {exc}") from exc
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise BoundCompareError(f"payload contains non-regular member: {relative}")
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise BoundCompareError(f"cannot read payload member {relative}: {exc}") from exc
        result[relative] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    if not result:
        raise BoundCompareError(f"payload is empty: {root}")
    return result


def closure_sha256(items: Mapping[str, Mapping[str, Any]]) -> str:
    value = hashlib.sha256()
    for relative, row in sorted(items.items()):
        value.update(relative.encode("utf-8"))
        value.update(b"\0")
        value.update(str(row["bytes"]).encode("ascii"))
        value.update(b"\0")
        value.update(str(row["sha256"]).encode("ascii"))
        value.update(b"\0")
    return value.hexdigest()


def validate_materialization(receipt: Mapping[str, Any]) -> dict[str, str]:
    try:
        identity = parent.validate_receipt(receipt)
    except parent.CompareError as exc:
        raise BoundCompareError(str(exc)) from exc
    source = strict_mapping(receipt.get("source"), "materialization source")
    ablation = strict_mapping(receipt.get("ablation"), "materialization ablation")
    if receipt.get("operation") != OPERATION:
        raise BoundCompareError("materialization operation mismatch")
    source_scheduler = digest(
        source.get("scheduler_sha256"), "source scheduler SHA-256"
    )
    ablation_scheduler = digest(
        ablation.get("scheduler_sha256"), "ablation scheduler SHA-256"
    )
    return {
        "source_closure": digest(
            identity.get("source_closure_sha256"), "source closure"
        ),
        "ablation_closure": digest(
            identity.get("ablation_closure_sha256"), "ablation closure"
        ),
        "source_scheduler": source_scheduler,
        "ablation_scheduler": ablation_scheduler,
    }


def _require_tree(
    root: Path,
    *,
    expected_inventory: Mapping[str, Mapping[str, Any]],
    expected_closure: str,
    expected_scheduler: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    actual = inventory(root)
    if actual != dict(expected_inventory):
        raise BoundCompareError(f"{label} payload inventory drifted")
    if closure_sha256(actual) != expected_closure:
        raise BoundCompareError(f"{label} payload closure drifted")
    scheduler = actual.get("scheduler.py")
    candidate = actual.get("candidate.py")
    if scheduler is None or scheduler.get("sha256") != expected_scheduler:
        raise BoundCompareError(f"{label} scheduler digest drifted")
    if candidate is None or candidate.get("sha256") != EXPECTED_ENTRY_SHA256:
        raise BoundCompareError(f"{label} candidate entry bytes drifted")
    return actual


def validate_binding(
    receipt: Mapping[str, Any],
    materialization: Mapping[str, Any],
    *,
    materialization_path: Path,
    bound_root: Path,
    source_root: Path,
    ablation_root: Path,
) -> dict[str, dict[str, str]]:
    if receipt.get("schema_version") != 1:
        raise BoundCompareError("execution-binding schema mismatch")
    if receipt.get("operation") != OPERATION:
        raise BoundCompareError("execution-binding operation mismatch")
    if receipt.get("repair") != EXPECTED_BINDING_REPAIR:
        raise BoundCompareError("execution-binding repair identity mismatch")
    if receipt.get("materialization_receipt_sha256") != file_sha256(
        materialization_path
    ):
        raise BoundCompareError(
            "execution binding does not name the exact materialization receipt"
        )

    expected = validate_materialization(materialization)
    source_inventory = inventory(source_root)
    ablation_inventory = inventory(ablation_root)
    if closure_sha256(source_inventory) != expected["source_closure"]:
        raise BoundCompareError("frozen V2 source changed after materialization")
    if closure_sha256(ablation_inventory) != expected["ablation_closure"]:
        raise BoundCompareError("ablation source changed after materialization")

    arms = strict_mapping(receipt.get("arms"), "execution-binding arms")
    if set(arms) != {"control", "ablation"}:
        raise BoundCompareError("execution-binding arm set is invalid")
    definitions = {
        "control": (
            source_inventory,
            expected["source_closure"],
            expected["source_scheduler"],
        ),
        "ablation": (
            ablation_inventory,
            expected["ablation_closure"],
            expected["ablation_scheduler"],
        ),
    }
    normalized: dict[str, dict[str, str]] = {}
    for arm, (expected_inventory, expected_closure, expected_scheduler) in definitions.items():
        row = strict_mapping(arms.get(arm), f"{arm} execution binding")
        if row.get("payload_closure_sha256") != expected_closure:
            raise BoundCompareError(f"{arm} binding closure is detached")
        if row.get("scheduler_sha256") != expected_scheduler:
            raise BoundCompareError(f"{arm} binding scheduler is detached")
        if row.get("payload_entry_sha256") != EXPECTED_ENTRY_SHA256:
            raise BoundCompareError(f"{arm} binding entry bytes drifted")
        if row.get("wrapper") != f"{arm}/bound_entry.py::agent":
            raise BoundCompareError(f"{arm} wrapper path/callable is invalid")
        _require_tree(
            Path(bound_root) / arm / "payload",
            expected_inventory=expected_inventory,
            expected_closure=expected_closure,
            expected_scheduler=expected_scheduler,
            label=arm,
        )
        wrapper_path = Path(bound_root) / arm / "bound_entry.py"
        try:
            wrapper = wrapper_path.read_bytes()
        except OSError as exc:
            raise BoundCompareError(f"cannot read {arm} wrapper: {exc}") from exc
        wrapper_sha = hashlib.sha256(wrapper).hexdigest()
        wrapper_blob = git_blob_sha1(wrapper)
        if row.get("wrapper_sha256") != wrapper_sha:
            raise BoundCompareError(f"{arm} wrapper SHA-256 drifted")
        if row.get("wrapper_git_blob_sha1") != wrapper_blob:
            raise BoundCompareError(f"{arm} wrapper Git blob drifted")
        normalized[arm] = {
            "payload_closure_sha256": expected_closure,
            "scheduler_sha256": expected_scheduler,
            "wrapper_sha256": wrapper_sha,
            "wrapper_git_blob_sha1": wrapper_blob,
        }
    if (
        normalized["control"]["wrapper_sha256"]
        == normalized["ablation"]["wrapper_sha256"]
    ):
        raise BoundCompareError("control and ablation wrapper identities are equal")
    return normalized


def validate_evaluator(
    receipt: Mapping[str, Any],
    *,
    source_path: Path,
    patched_path: Path,
) -> str:
    if receipt.get("schema_version") != 1:
        raise BoundCompareError("evaluator materialization schema mismatch")
    if receipt.get("operation") != OPERATION:
        raise BoundCompareError("evaluator materialization operation mismatch")
    if receipt.get("repair") != EXPECTED_EVALUATOR_REPAIR:
        raise BoundCompareError("evaluator materialization identity mismatch")
    source = strict_mapping(receipt.get("source"), "evaluator source")
    patched = strict_mapping(receipt.get("patched"), "patched evaluator")
    try:
        source_bytes = Path(source_path).read_bytes()
        patched_bytes = Path(patched_path).read_bytes()
    except OSError as exc:
        raise BoundCompareError(f"cannot read evaluator bytes: {exc}") from exc
    if git_blob_sha1(source_bytes) != EXPECTED_EVALUATOR_BLOB:
        raise BoundCompareError("source evaluator Git blob mismatch")
    if source.get("git_blob_sha1") != EXPECTED_EVALUATOR_BLOB:
        raise BoundCompareError("evaluator receipt source blob mismatch")
    if source.get("sha256") != hashlib.sha256(source_bytes).hexdigest():
        raise BoundCompareError("evaluator receipt source SHA-256 mismatch")
    if source.get("bytes") != len(source_bytes):
        raise BoundCompareError("evaluator receipt source length mismatch")
    patched_sha = hashlib.sha256(patched_bytes).hexdigest()
    if patched.get("sha256") != patched_sha:
        raise BoundCompareError("patched evaluator SHA-256 drifted")
    if patched.get("git_blob_sha1") != git_blob_sha1(patched_bytes):
        raise BoundCompareError("patched evaluator Git blob drifted")
    if patched.get("bytes") != len(patched_bytes):
        raise BoundCompareError("patched evaluator length drifted")
    if patched.get("candidate_action_field") != "candidate_action_sha256":
        raise BoundCompareError("candidate action digest field mismatch")
    if patched.get("candidate_action_count_field") != "candidate_action_count":
        raise BoundCompareError("candidate action count field mismatch")
    if patched.get("capture_phase") != (
        "after both returned actions, before interpreter"
    ):
        raise BoundCompareError("candidate action capture phase mismatch")
    patches = patched.get("patches")
    if not isinstance(patches, list) or len(patches) != 3:
        raise BoundCompareError("evaluator patch receipt is incomplete")
    for index, row_value in enumerate(patches):
        row = strict_mapping(row_value, f"evaluator patch {index}")
        if (
            row.get("old_occurrences_before") != 1
            or row.get("old_occurrences_after") != 0
            or row.get("new_occurrences_after") != 1
        ):
            raise BoundCompareError(
                f"evaluator patch {index} cardinality is invalid"
            )
    return patched_sha


def _fingerprint(path: Path, entry: str, callable_name: str = "agent") -> dict[str, str]:
    return {
        "entry": entry,
        "callable": callable_name,
        "sha256": file_sha256(path),
    }


def _engine_fingerprint(engine_dir: Path) -> dict[str, str]:
    root = Path(engine_dir)
    return {name: file_sha256(root / name) for name in EXPECTED_ENGINE_FILES}


def _validate_limits(value: Any, label: str) -> None:
    limits = strict_mapping(value, f"{label} limits")
    if set(limits) != set(EXPECTED_LIMITS):
        raise BoundCompareError(f"{label} limits keys mismatch")
    for key, expected in EXPECTED_LIMITS.items():
        actual = finite_number(limits.get(key), f"{label} limit {key}")
        if actual != expected:
            raise BoundCompareError(
                f"{label} limit {key} mismatch: expected {expected}, got {actual}"
            )


def _validate_progress(value: Any, label: str) -> None:
    progress = strict_mapping(value, f"{label} progress")
    if progress.get("state") != "complete" or progress.get("phase") != "finalize":
        raise BoundCompareError(f"{label} report was not atomically finalized")
    if strict_int(progress.get("planned_games"), f"{label} planned games") != 16:
        raise BoundCompareError(f"{label} planned-game cardinality mismatch")
    if strict_int(progress.get("recorded_games"), f"{label} recorded games") != 16:
        raise BoundCompareError(f"{label} recorded-game cardinality mismatch")
    if progress.get("active_game") is not None:
        raise BoundCompareError(f"{label} report retained an active game")
    if progress.get("recheck_requested") is not False:
        raise BoundCompareError(f"{label} recheck mode drifted")


def validate_game_grid(report: Mapping[str, Any], label: str) -> None:
    games = report.get("games")
    if not isinstance(games, list):
        raise BoundCompareError(f"{label} games is not a list")
    expected = {
        (opponent, seed, seat)
        for opponent in EXPECTED_OPPONENTS
        for seed in EXPECTED_SEEDS
        for seat in (0, 1)
    }
    observed: set[tuple[str, int, int]] = set()
    for index, value in enumerate(games):
        game = strict_mapping(value, f"{label} game {index}")
        opponent = game.get("opponent")
        seed = strict_int(game.get("seed"), f"{label} game {index} seed")
        seat = strict_int(
            game.get("candidate_seat"), f"{label} game {index} seat"
        )
        key = (opponent, seed, seat)
        if key not in expected or key in observed:
            raise BoundCompareError(
                f"{label} invalid or duplicate game identity {key!r}"
            )
        observed.add(key)
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise BoundCompareError(f"{label} incomplete game {key!r}")
        if "finalization_errors" in game:
            raise BoundCompareError(f"{label} finalization failed for {key!r}")
        if strict_int(game.get("episode_steps"), f"{label} episode steps") != (
            EXPECTED_EPISODE_STEPS
        ):
            raise BoundCompareError(f"{label} episode length drifted for {key!r}")
        if strict_int(game.get("steps"), f"{label} completed steps") != (
            EXPECTED_ACTION_COUNT
        ):
            raise BoundCompareError(f"{label} step coverage drifted for {key!r}")
        if strict_int(
            game.get("candidate_action_count"),
            f"{label} candidate action count",
        ) != EXPECTED_ACTION_COUNT:
            raise BoundCompareError(
                f"{label} candidate action coverage drifted for {key!r}"
            )
        digest(
            game.get("candidate_action_sha256"),
            f"{label} candidate action digest {key!r}",
        )
        digest(game.get("trace_sha256"), f"{label} whole trace {key!r}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise BoundCompareError(f"{label} score vector is invalid for {key!r}")
        finite_number(scores[0], f"{label} score 0 {key!r}")
        finite_number(scores[1], f"{label} score 1 {key!r}")
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise BoundCompareError(
            f"{label} exact grid mismatch; missing={missing}, extra={extra}"
        )


def validate_report_context(
    report: Mapping[str, Any],
    *,
    label: str,
    wrapper_sha256: str,
    evaluator_sha256: str,
    engine_dir: Path,
    loader_path: Path,
    arlene_path: Path,
    v1_path: Path,
) -> str:
    if report.get("schema_version") != 1:
        raise BoundCompareError(f"{label} schema mismatch")
    invocation = digest(report.get("invocation_id"), f"{label} invocation ID", 32)
    if report.get("engine_ref") != EXPECTED_ENGINE_REF:
        raise BoundCompareError(f"{label} engine ref mismatch")
    if report.get("engine_sha256") != _engine_fingerprint(engine_dir):
        raise BoundCompareError(f"{label} engine bytes mismatch")
    if report.get("loader_sha256") != file_sha256(loader_path):
        raise BoundCompareError(f"{label} loader bytes mismatch")
    if report.get("evaluator_sha256") != evaluator_sha256:
        raise BoundCompareError(f"{label} evaluator bytes mismatch")
    candidate = strict_mapping(report.get("candidate"), f"{label} candidate")
    expected_candidate = {
        "entry": "bound_entry.py",
        "callable": "agent",
        "sha256": wrapper_sha256,
    }
    if dict(candidate) != expected_candidate:
        raise BoundCompareError(f"{label} report is detached from its wrapper")
    opponents = strict_mapping(report.get("opponents"), f"{label} opponents")
    expected_opponents = {
        "arlene": _fingerprint(arlene_path, "arlene.py"),
        "v1": _fingerprint(v1_path, "candidate.py"),
    }
    if dict(opponents) != expected_opponents:
        raise BoundCompareError(f"{label} opponent bytes mismatch")
    seeds = report.get("seeds")
    if (
        not isinstance(seeds, list)
        or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)
        or tuple(seeds) != EXPECTED_SEEDS
    ):
        raise BoundCompareError(f"{label} exact seed tuple mismatch")
    if strict_int(report.get("agent_rng_seed"), f"{label} RNG seed") != (
        EXPECTED_RNG_SEED
    ):
        raise BoundCompareError(f"{label} RNG seed mismatch")
    _validate_limits(report.get("limits"), label)
    if report.get("method") != EXPECTED_METHOD:
        raise BoundCompareError(f"{label} evaluator method mismatch")
    if report.get("python") != sys.version or report.get("platform") != sys.platform:
        raise BoundCompareError(f"{label} Python/platform identity mismatch")
    _validate_progress(report.get("progress"), label)
    validate_game_grid(report, label)
    return invocation


def normalized_for_parent(report: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(report))
    candidate = dict(value["candidate"])
    candidate["sha256"] = EXPECTED_ENTRY_SHA256
    value["candidate"] = candidate
    for game in value["games"]:
        game["trace_sha256"] = game["candidate_action_sha256"]
    return value


def whole_trace_map(
    report: Mapping[str, Any],
) -> dict[tuple[str, int, int], str]:
    output: dict[tuple[str, int, int], str] = {}
    for index, game in enumerate(report["games"]):
        key = (
            game.get("opponent"),
            game.get("seed"),
            game.get("candidate_seat"),
        )
        if key in output:
            raise BoundCompareError(f"duplicate whole-trace key at game {index}")
        output[key] = digest(
            game.get("trace_sha256"), f"whole trace {index}"
        )
    return output


def apply_opponent_seat_gate(result: dict[str, Any]) -> None:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in result.get("rows", []):
        grouped[(str(row["opponent"]), strict_int(row["seat"], "result seat"))].append(
            row
        )
    expected = {
        (opponent, seat)
        for opponent in EXPECTED_OPPONENTS
        for seat in (0, 1)
    }
    if set(grouped) != expected:
        raise BoundCompareError("result opponent×seat strata are incomplete")
    strata: dict[str, dict[str, Any]] = {}
    regressed: list[str] = []
    for opponent, seat in sorted(expected):
        rows = grouped[(opponent, seat)]
        if len(rows) != len(EXPECTED_SEEDS):
            raise BoundCompareError(
                f"result stratum {opponent}/seat-{seat} cardinality mismatch"
            )
        deltas = [finite_number(row["own_delta"], "own delta") for row in rows]
        key = f"{opponent}/seat-{seat}"
        mean = statistics.mean(deltas)
        strata[key] = {
            "opponent": opponent,
            "seat": seat,
            "cells": len(rows),
            "positive_cells": sum(delta > 0 for delta in deltas),
            "zero_cells": sum(delta == 0 for delta in deltas),
            "negative_cells": sum(delta < 0 for delta in deltas),
            "mean_own_delta": mean,
            "minimum_own_delta": min(deltas),
            "maximum_own_delta": max(deltas),
        }
        if mean < 0:
            regressed.append(key)
    result["by_opponent_seat"] = strata
    if result.get("verdict") == "UPSIDE_SCREEN" and regressed:
        result["verdict"] = "SEAT_STRATUM_REGRESSION"
        result["reason"] = (
            "aggregate own cash passed, but one or more opponent×seat strata "
            "regressed on average: " + ", ".join(regressed)
        )
        result["exit_code"] = 1


def compare_bound(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    materialization: Mapping[str, Any],
    binding: Mapping[str, Any],
    evaluator_receipt: Mapping[str, Any],
    *,
    materialization_path: Path,
    bound_root: Path,
    source_root: Path,
    ablation_root: Path,
    evaluator_path: Path,
    source_evaluator_path: Path,
    engine_dir: Path,
    loader_path: Path,
    arlene_path: Path,
    v1_path: Path,
    git_head: str,
) -> dict[str, Any]:
    digest(git_head, "Git head", 40)
    arms = validate_binding(
        binding,
        materialization,
        materialization_path=materialization_path,
        bound_root=bound_root,
        source_root=source_root,
        ablation_root=ablation_root,
    )
    evaluator_sha = validate_evaluator(
        evaluator_receipt,
        source_path=source_evaluator_path,
        patched_path=evaluator_path,
    )
    control_invocation = validate_report_context(
        control,
        label="control",
        wrapper_sha256=arms["control"]["wrapper_sha256"],
        evaluator_sha256=evaluator_sha,
        engine_dir=engine_dir,
        loader_path=loader_path,
        arlene_path=arlene_path,
        v1_path=v1_path,
    )
    candidate_invocation = validate_report_context(
        candidate,
        label="candidate",
        wrapper_sha256=arms["ablation"]["wrapper_sha256"],
        evaluator_sha256=evaluator_sha,
        engine_dir=engine_dir,
        loader_path=loader_path,
        arlene_path=arlene_path,
        v1_path=v1_path,
    )
    if control_invocation == candidate_invocation:
        raise BoundCompareError("control and candidate invocation IDs are equal")

    control_whole = whole_trace_map(control)
    candidate_whole = whole_trace_map(candidate)
    if set(control_whole) != set(candidate_whole):
        raise BoundCompareError("whole-trace game grids differ")

    try:
        result = parent.compare(
            normalized_for_parent(control),
            normalized_for_parent(candidate),
            materialization,
            git_head=git_head,
        )
    except parent.CompareError as exc:
        raise BoundCompareError(str(exc)) from exc

    for row in result["rows"]:
        key = (row["opponent"], row["seed"], row["seat"])
        row["candidate_action_changed"] = row["trace_changed"]
        row["whole_trace_changed"] = (
            control_whole[key] != candidate_whole[key]
        )
    result["changed_rows"] = [
        row for row in result["rows"] if row["candidate_action_changed"]
    ]
    result["overall"]["candidate_action_changed_cells"] = result["overall"][
        "changed_cells"
    ]
    for values in result["by_opponent"].values():
        values["candidate_action_changed_cells"] = values["changed_cells"]
    apply_opponent_seat_gate(result)
    result["schema_version"] = 2
    result["exact_grid"] = {
        "seeds": list(EXPECTED_SEEDS),
        "opponents": list(EXPECTED_OPPONENTS),
        "seats": [0, 1],
        "paired_cells": 16,
        "games": 32,
    }
    result["execution_binding"] = {
        "control": arms["control"],
        "ablation": arms["ablation"],
        "patched_evaluator_sha256": evaluator_sha,
        "control_invocation_id": control_invocation,
        "candidate_invocation_id": candidate_invocation,
        "candidate_activation_field": "candidate_action_sha256",
        "candidate_activation_capture_phase": (
            "after both returned actions, before interpreter"
        ),
        "whole_trace_field": "trace_sha256",
        "expected_episode_steps": EXPECTED_EPISODE_STEPS,
        "post_game_payload_reverification": True,
    }
    return result


def markdown(report: Mapping[str, Any]) -> str:
    rendered = parent.markdown(report)
    rendered = rendered.replace(
        "Trace-changed cells", "Candidate-action-changed cells"
    )
    rendered = rendered.replace("Trace-changed", "Candidate-action-changed")
    rendered = rendered.replace(
        "returned action trace", "candidate returned-action digest"
    )
    binding = report.get("execution_binding")
    if not isinstance(binding, Mapping):
        return rendered
    lines = [
        "## Exact execution custody",
        "",
        f"- Control wrapper SHA-256: `{binding['control']['wrapper_sha256']}`",
        f"- Ablation wrapper SHA-256: `{binding['ablation']['wrapper_sha256']}`",
        f"- Patched evaluator SHA-256: `{binding['patched_evaluator_sha256']}`",
        "- Activation: candidate-only returned action, captured before interpretation",
        "- Coverage: exact four seeds × two opponents × two seats",
        "- Required episode: 719 returned actions / 720 configured steps",
        "- Payloads and wrappers reverified after both panels",
        "",
        "## Opponent × seat strata",
        "",
        "| Stratum | Cells | + / 0 / - | Mean own Δ | Min / max own Δ |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, value in report.get("by_opponent_seat", {}).items():
        lines.append(
            f"| {key} | {value['cells']} | "
            f"{value['positive_cells']} / {value['zero_cells']} / "
            f"{value['negative_cells']} | {value['mean_own_delta']:+.3f} | "
            f"{value['minimum_own_delta']:+.3f} / "
            f"{value['maximum_own_delta']:+.3f} |"
        )
    lines.append("")
    marker = "This is a one-factor offline causal screen"
    return rendered.replace(marker, "\n".join(lines) + "\n" + marker)


def atomic_write(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--materialization-receipt", type=Path, required=True)
    parser.add_argument("--binding-receipt", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--bound-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--ablation-root", type=Path, required=True)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--source-evaluator", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--arlene", type=Path, required=True)
    parser.add_argument("--v1", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    try:
        materialization = parent.strict_object(args.materialization_receipt)
        result = compare_bound(
            parent.strict_object(args.control),
            parent.strict_object(args.candidate),
            materialization,
            parent.strict_object(args.binding_receipt),
            parent.strict_object(args.evaluator_receipt),
            materialization_path=args.materialization_receipt,
            bound_root=args.bound_root,
            source_root=args.source_root,
            ablation_root=args.ablation_root,
            evaluator_path=args.evaluator,
            source_evaluator_path=args.source_evaluator,
            engine_dir=args.engine_dir,
            loader_path=args.loader,
            arlene_path=args.arlene,
            v1_path=args.v1,
            git_head=args.head,
        )
    except parent.CompareError as exc:
        result = {
            "schema_version": 2,
            "operation": OPERATION,
            "git_head": args.head,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
        }
    atomic_write(
        args.output,
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    atomic_write(args.markdown, markdown(result))
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "reason": result["reason"],
                "exit_code": result["exit_code"],
                "overall": result.get("overall"),
                "by_opponent": result.get("by_opponent"),
                "by_opponent_seat": result.get("by_opponent_seat"),
                "execution_binding": result.get("execution_binding"),
            },
            sort_keys=True,
        )
    )
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
