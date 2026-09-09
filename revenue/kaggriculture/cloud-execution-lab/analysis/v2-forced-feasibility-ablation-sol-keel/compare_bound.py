# SPDX-License-Identifier: Apache-2.0
"""Strictly compare closure-bound V2 control and forced-feasibility ablation."""
from __future__ import annotations

import argparse
import copy
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping

import bind_execution as binding_module
import compare as parent
import materialize as lane
import materialize_evaluator as evaluator_module

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
KAG = LAB.parent
ENGINE_DIR = LAB / "reference" / "engine"
LOADER = KAG / "20260907-offline-agent" / "evaluate.py"
ARLENE = (
    LAB
    / "runtime"
    / "variants"
    / "v1"
    / "reference"
    / "next-panel"
    / "vendor"
    / "arlene.py"
)
V1_ENTRY = LAB / "runtime" / "variants" / "v1" / "candidate.py"

OPERATION = lane.OPERATION
REPAIR = "sol-keel-closure-action-seat-custody-v1"
EXPECTED_EPISODE_STEPS = 720
EXPECTED_ACTIONS = 719
EXPECTED_SEEDS = (539131249, 1834999074, 2609097301, 2611092207)
EXPECTED_RNG_SEED = 20260909
EXPECTED_LIMITS = {
    "action_rpc_seconds": 1.0,
    "startup_seconds": 15.0,
    "game_seconds_between_steps": 180.0,
    "remaining_overage_time": 0.0,
}


class BoundCompareError(parent.CompareError):
    """Execution custody or candidate-only activation evidence is invalid."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Any, label: str, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise BoundCompareError(f"{label} is not a lowercase hex digest")
    return value


def mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BoundCompareError(f"{label} is not an object")
    return value


def exact_number(value: Any, expected: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BoundCompareError(f"{label} is not numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed != expected:
        raise BoundCompareError(
            f"{label} mismatch: expected {expected}, got {value!r}"
        )


def expected_environment() -> dict[str, Any]:
    files = {
        "kaggriculture.py": ENGINE_DIR / "kaggriculture.py",
        "kaggriculture.json": ENGINE_DIR / "kaggriculture.json",
        "utils.py": ENGINE_DIR / "utils.py",
    }
    return {
        "engine_ref": parent._load_base().ENGINE_REF,
        "engine_sha256": {
            name: file_sha256(path) for name, path in files.items()
        },
        "loader_sha256": file_sha256(LOADER),
        "opponents": {
            "arlene": {
                "entry": "arlene.py",
                "callable": "agent",
                "sha256": file_sha256(ARLENE),
            },
            "v1": {
                "entry": "candidate.py",
                "callable": "agent",
                "sha256": file_sha256(V1_ENTRY),
            },
        },
    }


def validate_materialization(receipt: Mapping[str, Any]) -> dict[str, str]:
    try:
        parent_identity = parent.validate_receipt(receipt)
        binding_identity = binding_module.validate_materialization(receipt)
    except (parent.CompareError, binding_module.BindingError) as exc:
        raise BoundCompareError(str(exc)) from exc
    if parent_identity["source_closure_sha256"] != binding_identity[
        "source_closure"
    ]:
        raise BoundCompareError("source closure validators disagree")
    if parent_identity["ablation_closure_sha256"] != binding_identity[
        "ablation_closure"
    ]:
        raise BoundCompareError("ablation closure validators disagree")
    return binding_identity


def validate_binding(
    receipt: Mapping[str, Any],
    materialization_path: Path,
    materialization: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    if receipt.get("schema_version") != 1:
        raise BoundCompareError("execution-binding schema mismatch")
    if receipt.get("operation") != OPERATION:
        raise BoundCompareError("execution-binding operation mismatch")
    if receipt.get("repair") != binding_module.REPAIR:
        raise BoundCompareError("execution-binding repair identity mismatch")
    if receipt.get("materialization_receipt_sha256") != file_sha256(
        materialization_path
    ):
        raise BoundCompareError(
            "execution binding does not name the exact materialization receipt"
        )
    material = validate_materialization(materialization)
    arms = mapping(receipt.get("arms"), "execution-binding arms")
    if set(arms) != {"control", "ablation"}:
        raise BoundCompareError("execution-binding arm set is invalid")
    expected = {
        "control": (
            material["source_closure"],
            material["source_scheduler"],
        ),
        "ablation": (
            material["ablation_closure"],
            material["ablation_scheduler"],
        ),
    }
    normalized: dict[str, dict[str, str]] = {}
    for arm, (closure, scheduler) in expected.items():
        row = mapping(arms.get(arm), f"{arm} execution binding")
        if row.get("payload_closure_sha256") != closure:
            raise BoundCompareError(f"{arm} payload closure is detached")
        if row.get("scheduler_sha256") != scheduler:
            raise BoundCompareError(f"{arm} scheduler digest is detached")
        if row.get("payload_entry_sha256") != (
            binding_module.EXPECTED_ENTRY_SHA256
        ):
            raise BoundCompareError(f"{arm} payload entry bytes drifted")
        if row.get("wrapper") != f"{arm}/bound_entry.py::agent":
            raise BoundCompareError(f"{arm} wrapper path/callable is invalid")
        normalized[arm] = {
            "payload_closure_sha256": closure,
            "scheduler_sha256": scheduler,
            "wrapper_sha256": digest(
                row.get("wrapper_sha256"), f"{arm} wrapper"
            ),
            "wrapper_git_blob_sha1": digest(
                row.get("wrapper_git_blob_sha1"),
                f"{arm} wrapper Git blob",
                40,
            ),
        }
    if normalized["control"]["wrapper_sha256"] == normalized["ablation"][
        "wrapper_sha256"
    ]:
        raise BoundCompareError("control and ablation wrappers are equal")
    return normalized


def validate_live_arms(
    arms: Mapping[str, Mapping[str, str]], arms_root: Path
) -> None:
    helper = lane._load_base()
    root = arms_root.resolve(strict=True)
    for arm, expected in arms.items():
        arm_root = root / arm
        payload = arm_root / "payload"
        wrapper = arm_root / "bound_entry.py"
        inventory = helper.inventory(payload)
        if helper.closure_sha256(inventory) != expected[
            "payload_closure_sha256"
        ]:
            raise BoundCompareError(f"{arm} live payload closure drifted")
        if inventory.get("scheduler.py", {}).get("sha256") != expected[
            "scheduler_sha256"
        ]:
            raise BoundCompareError(f"{arm} live scheduler drifted")
        if inventory.get("candidate.py", {}).get("sha256") != (
            binding_module.EXPECTED_ENTRY_SHA256
        ):
            raise BoundCompareError(f"{arm} live payload entry drifted")
        data = wrapper.read_bytes()
        if helper.sha256(data) != expected["wrapper_sha256"]:
            raise BoundCompareError(f"{arm} live wrapper SHA-256 drifted")
        if helper.git_blob_sha1(data) != expected["wrapper_git_blob_sha1"]:
            raise BoundCompareError(f"{arm} live wrapper Git blob drifted")


def validate_evaluator(
    receipt: Mapping[str, Any], patched_path: Path
) -> str:
    if receipt.get("schema_version") != 1:
        raise BoundCompareError("evaluator materialization schema mismatch")
    if receipt.get("operation") != OPERATION:
        raise BoundCompareError("evaluator operation mismatch")
    if receipt.get("repair") != evaluator_module.REPAIR:
        raise BoundCompareError("evaluator materialization identity mismatch")
    source = mapping(receipt.get("source"), "evaluator source")
    patched = mapping(receipt.get("patched"), "patched evaluator")
    if source.get("git_blob_sha1") != evaluator_module.EXPECTED_EVALUATOR_BLOB:
        raise BoundCompareError("evaluator source blob mismatch")
    if source.get("sha256") != file_sha256(KAG / "cloud-eval" / "evaluate.py"):
        raise BoundCompareError("evaluator source SHA-256 mismatch")
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
    for index, row in enumerate(patches):
        row = mapping(row, f"evaluator patch {index}")
        if (
            row.get("old_occurrences_before") != 1
            or row.get("old_occurrences_after") != 0
            or row.get("new_occurrences_after") != 1
        ):
            raise BoundCompareError(
                f"evaluator patch {index} cardinality is invalid"
            )
    expected_sha = digest(patched.get("sha256"), "patched evaluator")
    data = patched_path.resolve(strict=True).read_bytes()
    helper = lane._load_base()
    if helper.sha256(data) != expected_sha:
        raise BoundCompareError("live patched evaluator SHA-256 drifted")
    if helper.git_blob_sha1(data) != patched.get("git_blob_sha1"):
        raise BoundCompareError("live patched evaluator Git blob drifted")
    return expected_sha


def validate_invocation(value: Any, label: str) -> str:
    return digest(value, label, 32)


def validate_report_binding(
    report: Mapping[str, Any],
    *,
    arm: str,
    wrapper_sha256: str,
    evaluator_sha256: str,
) -> str:
    environment = expected_environment()
    if report.get("schema_version") != 1:
        raise BoundCompareError(f"{arm} report schema mismatch")
    invocation = validate_invocation(
        report.get("invocation_id"), f"{arm} invocation"
    )
    if report.get("engine_ref") != environment["engine_ref"]:
        raise BoundCompareError(f"{arm} engine ref mismatch")
    if report.get("engine_sha256") != environment["engine_sha256"]:
        raise BoundCompareError(f"{arm} engine source map mismatch")
    if report.get("loader_sha256") != environment["loader_sha256"]:
        raise BoundCompareError(f"{arm} loader mismatch")
    if report.get("evaluator_sha256") != evaluator_sha256:
        raise BoundCompareError(
            f"{arm} report was not emitted by the patched evaluator"
        )

    candidate = mapping(report.get("candidate"), f"{arm} report candidate")
    if candidate.get("entry") != "bound_entry.py":
        raise BoundCompareError(f"{arm} report used the wrong entry file")
    if candidate.get("callable") != "agent":
        raise BoundCompareError(f"{arm} report used the wrong callable")
    if candidate.get("sha256") != wrapper_sha256:
        raise BoundCompareError(
            f"{arm} report is not bound to its closure-verifying wrapper"
        )
    if report.get("opponents") != environment["opponents"]:
        raise BoundCompareError(f"{arm} opponent bank mismatch")
    seeds = report.get("seeds")
    if (
        not isinstance(seeds, list)
        or tuple(seeds) != EXPECTED_SEEDS
        or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)
    ):
        raise BoundCompareError(f"{arm} exact seed grid mismatch")
    if report.get("agent_rng_seed") != EXPECTED_RNG_SEED:
        raise BoundCompareError(f"{arm} agent RNG seed mismatch")
    python = report.get("python")
    platform = report.get("platform")
    method = report.get("method")
    if not isinstance(python, str) or not python:
        raise BoundCompareError(f"{arm} Python identity missing")
    if not isinstance(platform, str) or not platform:
        raise BoundCompareError(f"{arm} platform identity missing")
    if not isinstance(method, str) or "Official interpreter" not in method:
        raise BoundCompareError(f"{arm} evaluator method identity missing")
    limits = mapping(report.get("limits"), f"{arm} limits")
    if set(limits) != set(EXPECTED_LIMITS):
        raise BoundCompareError(f"{arm} limit keys mismatch")
    for key, expected in EXPECTED_LIMITS.items():
        exact_number(limits.get(key), expected, f"{arm} limit {key}")

    progress = mapping(report.get("progress"), f"{arm} progress")
    if (
        progress.get("state") != "complete"
        or progress.get("phase") != "finalize"
        or progress.get("planned_games") != 16
        or progress.get("recorded_games") != 16
        or progress.get("active_game") is not None
    ):
        raise BoundCompareError(f"{arm} final progress receipt is incomplete")

    rows = report.get("games")
    if not isinstance(rows, list) or len(rows) != 16:
        raise BoundCompareError(f"{arm} games must contain exactly 16 cells")
    for index, game in enumerate(rows):
        game = mapping(game, f"{arm} game {index}")
        seat = game.get("candidate_seat")
        if isinstance(seat, bool) or not isinstance(seat, int) or seat not in (0, 1):
            raise BoundCompareError(f"{arm} game {index} seat is invalid")
        steps = game.get("steps")
        episode_steps = game.get("episode_steps")
        if (
            isinstance(steps, bool)
            or not isinstance(steps, int)
            or isinstance(episode_steps, bool)
            or not isinstance(episode_steps, int)
            or episode_steps != EXPECTED_EPISODE_STEPS
            or steps != EXPECTED_ACTIONS
        ):
            raise BoundCompareError(
                f"{arm} game {index} does not cover the official episode"
            )
        count = game.get("candidate_action_count")
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or count != EXPECTED_ACTIONS
        ):
            raise BoundCompareError(
                f"{arm} game {index} candidate action count is invalid"
            )
        digest(
            game.get("candidate_action_sha256"),
            f"{arm} game {index} candidate action digest",
        )
        digest(game.get("trace_sha256"), f"{arm} game {index} whole trace")
    return invocation


def normalized_for_parent(report: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(report))
    candidate = dict(value["candidate"])
    candidate["sha256"] = binding_module.EXPECTED_ENTRY_SHA256
    value["candidate"] = candidate
    for game in value["games"]:
        game["trace_sha256"] = game["candidate_action_sha256"]
    return value


def whole_trace_map(
    report: Mapping[str, Any]
) -> dict[tuple[str, int, int], str]:
    output: dict[tuple[str, int, int], str] = {}
    for index, game in enumerate(report["games"]):
        key = (
            game.get("opponent"),
            game.get("seed"),
            game.get("candidate_seat"),
        )
        if key in output:
            raise BoundCompareError(f"duplicate whole-trace cell {key!r}")
        output[key] = digest(
            game.get("trace_sha256"), f"whole trace {index}"
        )
    return output


def subgroup_receipts(
    rows: list[Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    grouped: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["opponent"]), int(row["seat"]))].append(row)
    expected = {
        (opponent, seat)
        for opponent in ("arlene", "v1")
        for seat in (0, 1)
    }
    if set(grouped) != expected:
        raise BoundCompareError("opponent-by-seat subgroup grid mismatch")
    result: dict[str, dict[str, Any]] = {}
    for (opponent, seat), values in sorted(grouped.items()):
        own = [float(row["own_delta"]) for row in values]
        margin = [float(row["margin_delta"]) for row in values]
        result[f"{opponent}:seat{seat}"] = {
            "opponent": opponent,
            "seat": seat,
            "cells": len(values),
            "candidate_action_changed_cells": sum(
                bool(row["candidate_action_changed"]) for row in values
            ),
            "positive_cells": sum(value > 0 for value in own),
            "zero_cells": sum(value == 0 for value in own),
            "negative_cells": sum(value < 0 for value in own),
            "mean_own_delta": statistics.mean(own),
            "median_own_delta": statistics.median(own),
            "minimum_own_delta": min(own),
            "maximum_own_delta": max(own),
            "mean_margin_delta": statistics.mean(margin),
        }
    return result


def compare_bound(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    materialization: Mapping[str, Any],
    binding: Mapping[str, Any],
    evaluator: Mapping[str, Any],
    *,
    materialization_path: Path,
    arms_root: Path,
    patched_evaluator_path: Path,
    git_head: str,
) -> dict[str, Any]:
    digest(git_head, "git head", 40)
    arms = validate_binding(binding, materialization_path, materialization)
    validate_live_arms(arms, arms_root)
    evaluator_sha = validate_evaluator(evaluator, patched_evaluator_path)
    control_invocation = validate_report_binding(
        control,
        arm="control",
        wrapper_sha256=arms["control"]["wrapper_sha256"],
        evaluator_sha256=evaluator_sha,
    )
    candidate_invocation = validate_report_binding(
        candidate,
        arm="ablation",
        wrapper_sha256=arms["ablation"]["wrapper_sha256"],
        evaluator_sha256=evaluator_sha,
    )
    if control_invocation == candidate_invocation:
        raise BoundCompareError("control and ablation invocation IDs are equal")
    if (
        control.get("python") != candidate.get("python")
        or control.get("platform") != candidate.get("platform")
        or control.get("method") != candidate.get("method")
    ):
        raise BoundCompareError("control/ablation execution context drift")

    control_whole = whole_trace_map(control)
    candidate_whole = whole_trace_map(candidate)
    if set(control_whole) != set(candidate_whole):
        raise BoundCompareError("whole-trace game grids differ")

    result = parent.compare(
        normalized_for_parent(control),
        normalized_for_parent(candidate),
        materialization,
        git_head=git_head,
    )
    for row in result["rows"]:
        key = (row["opponent"], row["seed"], row["seat"])
        row["candidate_action_changed"] = bool(row["trace_changed"])
        row["whole_trace_changed"] = control_whole[key] != candidate_whole[key]
    result["changed_rows"] = [
        row for row in result["rows"] if row["candidate_action_changed"]
    ]
    result["overall"]["candidate_action_changed_cells"] = result["overall"][
        "changed_cells"
    ]
    result["overall"]["whole_trace_changed_cells"] = sum(
        row["whole_trace_changed"] for row in result["rows"]
    )
    for values in result["by_opponent"].values():
        values["candidate_action_changed_cells"] = values["changed_cells"]

    by_opponent_seat = subgroup_receipts(result["rows"])
    result["by_opponent_seat"] = by_opponent_seat
    own_deltas = [float(row["own_delta"]) for row in result["rows"]]
    rival_deltas = [float(row["rival_delta"]) for row in result["rows"]]
    changed = result["overall"]["candidate_action_changed_cells"]

    if changed == 0:
        verdict = "NO_ACTION_SIGNAL"
        reason = (
            "the forced-feasibility admission/rank ablation never changed a "
            "candidate returned-action digest"
        )
        exit_code = 4
    elif all(value == 0 for value in own_deltas + rival_deltas):
        verdict = "ACTION_NO_SCORE_SIGNAL"
        reason = (
            "candidate actions changed, but every terminal score remained identical"
        )
        exit_code = 4
    elif (
        result["overall"]["mean_own_delta"] > 0
        and result["overall"]["median_own_delta"] >= 0
        and result["overall"]["positive_cells"]
        >= result["overall"]["negative_cells"]
        and all(
            values["mean_own_delta"] >= 0
            for values in result["by_opponent"].values()
        )
        and all(
            values["mean_own_delta"] >= 0
            for values in by_opponent_seat.values()
        )
    ):
        verdict = "UPSIDE_SCREEN"
        reason = (
            "the one-factor ablation improved mean own cash, did not lower "
            "median own cash, and did not regress any opponent or "
            "opponent-by-seat subgroup on average"
        )
        exit_code = 0
    elif result["overall"]["mean_own_delta"] < 0:
        verdict = "REGRESSION"
        reason = "the one-factor ablation lowered mean own cash"
        exit_code = 1
    else:
        verdict = "MIXED"
        reason = (
            "the one-factor ablation changed play without broad own-cash "
            "upside across every opponent-by-seat subgroup"
        )
        exit_code = 1

    result["verdict"] = verdict
    result["reason"] = reason
    result["exit_code"] = exit_code
    result["schema_version"] = 2
    result["operation"] = OPERATION
    result["repair"] = REPAIR
    result["execution_binding"] = {
        "control": arms["control"],
        "ablation": arms["ablation"],
        "control_invocation_id": control_invocation,
        "ablation_invocation_id": candidate_invocation,
        "patched_evaluator_sha256": evaluator_sha,
        "candidate_activation_field": "candidate_action_sha256",
        "candidate_activation_capture_phase": (
            "after both returned actions, before interpreter"
        ),
        "whole_trace_field": "trace_sha256",
        "expected_episode_steps": EXPECTED_EPISODE_STEPS,
        "expected_candidate_actions": EXPECTED_ACTIONS,
        "opponent_by_seat_non_regression_required": True,
    }
    return result


def markdown(report: Mapping[str, Any]) -> str:
    if report.get("verdict") == "INVALID":
        return (
            "# TITAN V2 forced-feasibility admission/rank ablation\n\n"
            f"- Verdict: **INVALID**\n- Reason: {report.get('reason')}\n"
        )
    text = parent.markdown(report)
    text = text.replace("Trace-changed cells", "Candidate-action-changed cells")
    text = text.replace("Trace-changed", "Candidate-action-changed")
    text = text.replace("returned action trace", "candidate returned-action digest")
    binding = report.get("execution_binding")
    subgroup = report.get("by_opponent_seat")
    if binding:
        lines = [
            "",
            "## Execution custody",
            "",
            f"- Control wrapper SHA-256: `{binding['control']['wrapper_sha256']}`",
            f"- Ablation wrapper SHA-256: `{binding['ablation']['wrapper_sha256']}`",
            f"- Patched evaluator SHA-256: `{binding['patched_evaluator_sha256']}`",
            f"- Control invocation: `{binding['control_invocation_id']}`",
            f"- Ablation invocation: `{binding['ablation_invocation_id']}`",
            "- Activation: candidate-only pre-interpreter returned-action digest",
            "- Required episode: 719 returned actions / 720 configured steps",
            "- Admission: every opponent×seat mean own-cash delta must be nonnegative",
            "",
        ]
        text += "\n".join(lines)
    if subgroup:
        lines = [
            "## Opponent × seat own-cash gate",
            "",
            "| subgroup | cells | changed | mean own Δ | min own Δ |",
            "|---|---:|---:|---:|---:|",
        ]
        for key, values in sorted(subgroup.items()):
            lines.append(
                f"| {key} | {values['cells']} | "
                f"{values['candidate_action_changed_cells']} | "
                f"{values['mean_own_delta']:.6f} | "
                f"{values['minimum_own_delta']:.6f} |"
            )
        text += "\n" + "\n".join(lines) + "\n"
    return text


def atomic_write(path: Path, text: str) -> None:
    lane._load_base().atomic_write(path, text.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--materialization-receipt", type=Path, required=True)
    parser.add_argument("--binding-receipt", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--arms-root", type=Path, required=True)
    parser.add_argument("--patched-evaluator", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    try:
        materialization = parent.strict_object(args.materialization_receipt)
        report = compare_bound(
            parent.strict_object(args.control),
            parent.strict_object(args.candidate),
            materialization,
            parent.strict_object(args.binding_receipt),
            parent.strict_object(args.evaluator_receipt),
            materialization_path=args.materialization_receipt,
            arms_root=args.arms_root,
            patched_evaluator_path=args.patched_evaluator,
            git_head=args.head,
        )
    except (BoundCompareError, parent.CompareError, OSError) as exc:
        report = {
            "schema_version": 2,
            "operation": OPERATION,
            "repair": REPAIR,
            "git_head": args.head,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
        }
    atomic_write(
        args.output,
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    atomic_write(args.markdown, markdown(report))
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "reason": report["reason"],
                "exit_code": report["exit_code"],
                "overall": report.get("overall"),
                "by_opponent": report.get("by_opponent"),
                "by_opponent_seat": report.get("by_opponent_seat"),
            },
            sort_keys=True,
        )
    )
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
