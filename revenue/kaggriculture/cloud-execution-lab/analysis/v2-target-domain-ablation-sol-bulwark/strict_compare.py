# SPDX-License-Identifier: Apache-2.0
"""Closure/grid-bound admission layer for the V2 target-domain causal screen."""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping

import bind_execution
import compare
import materialize


EXPECTED_GAMES = (
    len(bind_execution.EXPECTED_SEEDS)
    * len(bind_execution.EXPECTED_OPPONENTS)
    * 2
)


class StrictCompareError(ValueError):
    """The reports are not the exact closure-bound paired experiment."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise StrictCompareError(f"{label} is not an object")
    return value


def _sha256_text(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise StrictCompareError(f"{label} is not a lowercase SHA-256 digest")
    return value


def _head(value: Any) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise StrictCompareError("git head is not a lowercase 40-hex commit")
    return value


def _file_sha256(path: Path, label: str) -> str:
    try:
        if not path.is_file() or path.is_symlink():
            raise StrictCompareError(f"{label} is not one regular file: {path}")
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise StrictCompareError(f"cannot read {label} {path}: {exc}") from exc


def _exact_limits(value: Any, label: str) -> dict[str, Any]:
    mapping = _mapping(value, label)
    expected = bind_execution.EXPECTED_LIMITS
    if set(mapping) != set(expected):
        raise StrictCompareError(f"{label} keys differ from the exact limit contract")
    output: dict[str, Any] = {}
    for key, wanted in expected.items():
        actual = mapping.get(key)
        if (
            isinstance(actual, bool)
            or not isinstance(actual, (int, float))
            or not math.isfinite(float(actual))
            or float(actual) != float(wanted)
        ):
            raise StrictCompareError(f"{label}.{key} differs from {wanted!r}")
        output[key] = actual
    return output


def _validate_fingerprint(
    value: Any,
    expected: Mapping[str, Any],
    label: str,
) -> dict[str, Any]:
    mapping = _mapping(value, label)
    if dict(mapping) != dict(expected):
        raise StrictCompareError(f"{label} does not match execution binding")
    _sha256_text(mapping.get("sha256"), f"{label}.sha256")
    entry = mapping.get("entry")
    callable_name = mapping.get("callable")
    if not isinstance(entry, str) or not entry or callable_name != "agent":
        raise StrictCompareError(f"{label} entry/callable is invalid")
    return dict(mapping)


def validate_binding(
    binding: Mapping[str, Any],
    receipt: Mapping[str, Any],
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
    """Recompute every on-disk identity named by the execution receipt."""
    git_head = _head(git_head)
    if binding.get("schema_version") != 1:
        raise StrictCompareError("execution binding schema mismatch")
    if binding.get("operation") != (
        "titan-v2-target-domain-execution-binding-20260909-sol-janus-01"
    ):
        raise StrictCompareError("execution binding operation mismatch")
    if binding.get("git_head") != git_head:
        raise StrictCompareError("execution binding git head mismatch")

    expected_seeds = list(bind_execution.EXPECTED_SEEDS)
    seeds = binding.get("seeds")
    if (
        not isinstance(seeds, list)
        or seeds != expected_seeds
        or any(type(seed) is not int for seed in seeds)
    ):
        raise StrictCompareError("execution binding seed grid is not exact")
    if binding.get("agent_rng_seed") != bind_execution.EXPECTED_AGENT_RNG_SEED:
        raise StrictCompareError("execution binding RNG seed mismatch")
    limits = _exact_limits(binding.get("limits"), "execution binding limits")
    if binding.get("python") != __import__("sys").version:
        raise StrictCompareError("execution binding Python version drift")
    if binding.get("platform") != __import__("sys").platform:
        raise StrictCompareError("execution binding platform drift")

    closure = compare.validate_receipt(receipt)
    arms = _mapping(binding.get("arms"), "execution binding arms")
    if set(arms) != {"control", "candidate"}:
        raise StrictCompareError("execution binding arm set is invalid")

    control_root = control_root.resolve()
    candidate_root = candidate_root.resolve()
    actual_closures = {
        "control": materialize.closure_sha256(materialize.inventory(control_root)),
        "candidate": materialize.closure_sha256(materialize.inventory(candidate_root)),
    }
    expected_closures = {
        "control": closure["source_closure_sha256"],
        "candidate": closure["ablation_closure_sha256"],
    }
    wrapper_paths = {
        "control": control_wrapper.resolve(),
        "candidate": candidate_wrapper.resolve(),
    }
    checked_arms: dict[str, Any] = {}
    for label in ("control", "candidate"):
        arm = _mapping(arms.get(label), f"execution binding {label} arm")
        if arm.get("closure_sha256") != expected_closures[label]:
            raise StrictCompareError(f"{label} arm is not bound to materialization")
        if actual_closures[label] != expected_closures[label]:
            raise StrictCompareError(f"{label} root closure changed before classification")
        if arm.get("candidate_entry_sha256") != compare.V2_ENTRY_SHA256:
            raise StrictCompareError(f"{label} original entrypoint identity drift")
        root = control_root if label == "control" else candidate_root
        if _file_sha256(root / "candidate.py", f"{label} candidate.py") != (
            compare.V2_ENTRY_SHA256
        ):
            raise StrictCompareError(f"{label} candidate.py bytes drifted")
        expected_wrapper = {
            "entry": wrapper_paths[label].name,
            "callable": "agent",
            "sha256": _file_sha256(
                wrapper_paths[label], f"{label} closure wrapper"
            ),
        }
        wrapper = _validate_fingerprint(
            arm.get("wrapper"),
            expected_wrapper,
            f"execution binding {label} wrapper",
        )
        checked_arms[label] = {
            "closure_sha256": expected_closures[label],
            "candidate_entry_sha256": compare.V2_ENTRY_SHA256,
            "wrapper": wrapper,
        }

    if checked_arms["control"]["wrapper"]["sha256"] == (
        checked_arms["candidate"]["wrapper"]["sha256"]
    ):
        raise StrictCompareError("control and candidate wrapper identities are equal")

    engine_mapping = _mapping(
        binding.get("engine_sha256"), "execution binding engine hashes"
    )
    if set(engine_mapping) != set(bind_execution.EXPECTED_ENGINE_FILES):
        raise StrictCompareError("execution binding engine file set is invalid")
    actual_engine = {
        name: _file_sha256(
            engine_dir.resolve() / name,
            f"engine {name}",
        )
        for name in bind_execution.EXPECTED_ENGINE_FILES
    }
    if dict(engine_mapping) != actual_engine:
        raise StrictCompareError("execution binding engine bytes changed")

    actual_loader = _file_sha256(loader.resolve(), "loader")
    actual_evaluator = _file_sha256(evaluator.resolve(), "evaluator")
    if binding.get("loader_sha256") != actual_loader:
        raise StrictCompareError("execution binding loader bytes changed")
    if binding.get("evaluator_sha256") != actual_evaluator:
        raise StrictCompareError("execution binding evaluator bytes changed")

    if tuple(sorted(opponents)) != tuple(sorted(bind_execution.EXPECTED_OPPONENTS)):
        raise StrictCompareError("classification opponent bank mismatch")
    actual_opponents = {
        name: bind_execution._fingerprint_spec(
            opponents[name],
            f"opponent {name}",
        )
        for name in bind_execution.EXPECTED_OPPONENTS
    }
    bound_opponents = _mapping(
        binding.get("opponents"), "execution binding opponents"
    )
    if dict(bound_opponents) != actual_opponents:
        raise StrictCompareError("execution binding opponent bytes changed")
    for name in bind_execution.EXPECTED_OPPONENTS:
        _validate_fingerprint(
            bound_opponents[name],
            actual_opponents[name],
            f"execution binding opponent {name}",
        )

    return {
        "git_head": git_head,
        "arms": checked_arms,
        "engine_sha256": actual_engine,
        "loader_sha256": actual_loader,
        "evaluator_sha256": actual_evaluator,
        "opponents": actual_opponents,
        "seeds": expected_seeds,
        "agent_rng_seed": bind_execution.EXPECTED_AGENT_RNG_SEED,
        "limits": limits,
        "python": binding["python"],
        "platform": binding["platform"],
    }


def validate_report(
    report: Mapping[str, Any],
    *,
    label: str,
    binding: Mapping[str, Any],
) -> str:
    """Require one exact evaluator invocation for the named bound arm."""
    if report.get("schema_version") != 1:
        raise StrictCompareError(f"{label} report schema mismatch")
    invocation = report.get("invocation_id")
    if (
        not isinstance(invocation, str)
        or len(invocation) != 32
        or any(char not in "0123456789abcdef" for char in invocation)
    ):
        raise StrictCompareError(f"{label} invocation_id is not 32 lowercase hex")

    _validate_fingerprint(
        report.get("candidate"),
        binding["arms"][label]["wrapper"],
        f"{label} candidate wrapper",
    )
    if report.get("engine_sha256") != binding["engine_sha256"]:
        raise StrictCompareError(f"{label} engine identity mismatch")
    if report.get("loader_sha256") != binding["loader_sha256"]:
        raise StrictCompareError(f"{label} loader identity mismatch")
    if report.get("evaluator_sha256") != binding["evaluator_sha256"]:
        raise StrictCompareError(f"{label} evaluator identity mismatch")
    if report.get("opponents") != binding["opponents"]:
        raise StrictCompareError(f"{label} opponent identity mismatch")
    if report.get("seeds") != binding["seeds"]:
        raise StrictCompareError(f"{label} seed grid mismatch")
    if report.get("agent_rng_seed") != binding["agent_rng_seed"]:
        raise StrictCompareError(f"{label} RNG seed mismatch")
    _exact_limits(report.get("limits"), f"{label} limits")
    if report.get("python") != binding["python"]:
        raise StrictCompareError(f"{label} Python version mismatch")
    if report.get("platform") != binding["platform"]:
        raise StrictCompareError(f"{label} platform mismatch")
    method = report.get("method")
    if not isinstance(method, str) or not method:
        raise StrictCompareError(f"{label} method is missing")

    games = report.get("games")
    if not isinstance(games, list) or len(games) != EXPECTED_GAMES:
        raise StrictCompareError(
            f"{label} must contain exactly {EXPECTED_GAMES} games"
        )
    for index, game in enumerate(games):
        if not isinstance(game, Mapping):
            raise StrictCompareError(f"{label} game {index} is not an object")
        if type(game.get("candidate_seat")) is not int:
            raise StrictCompareError(
                f"{label} game {index} candidate_seat is not a literal integer"
            )
        if type(game.get("seed")) is not int:
            raise StrictCompareError(
                f"{label} game {index} seed is not a literal integer"
            )
        if type(game.get("opponent")) is not str:
            raise StrictCompareError(
                f"{label} game {index} opponent is not a string"
            )
    return invocation


def _normalized_for_core(report: Mapping[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(dict(report))
    normalized["candidate"] = {
        "entry": "candidate.py",
        "callable": "agent",
        "sha256": compare.V2_ENTRY_SHA256,
    }
    return normalized


def _strata(rows: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[tuple[str, int], list[float]] = defaultdict(list)
    changed: dict[tuple[str, int], int] = defaultdict(int)
    for row in rows:
        key = (str(row["opponent"]), int(row["seat"]))
        delta = float(row["own_delta"])
        grouped[key].append(delta)
        changed[key] += int(bool(row["trace_changed"]))
    output: dict[str, dict[str, Any]] = {}
    for (opponent, seat), deltas in sorted(grouped.items()):
        key = f"{opponent}:seat-{seat}"
        output[key] = {
            "opponent": opponent,
            "seat": seat,
            "cells": len(deltas),
            "changed_cells": changed[(opponent, seat)],
            "positive_cells": sum(delta > 0 for delta in deltas),
            "zero_cells": sum(delta == 0 for delta in deltas),
            "negative_cells": sum(delta < 0 for delta in deltas),
            "mean_own_delta": statistics.mean(deltas),
            "median_own_delta": statistics.median(deltas),
            "minimum_own_delta": min(deltas),
            "maximum_own_delta": max(deltas),
        }
    expected = {
        f"{opponent}:seat-{seat}"
        for opponent in bind_execution.EXPECTED_OPPONENTS
        for seat in (0, 1)
    }
    if set(output) != expected:
        raise StrictCompareError("opponent-by-seat stratum set is incomplete")
    return output


def compare_bound(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    receipt: Mapping[str, Any],
    execution_binding: Mapping[str, Any],
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
    binding = validate_binding(
        execution_binding,
        receipt,
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
    control_invocation = validate_report(
        control,
        label="control",
        binding=binding,
    )
    candidate_invocation = validate_report(
        candidate,
        label="candidate",
        binding=binding,
    )
    if control_invocation == candidate_invocation:
        raise StrictCompareError("control and candidate invocation IDs are equal")
    if control.get("method") != candidate.get("method"):
        raise StrictCompareError("control/candidate evaluation method drift")

    report = compare.compare(
        _normalized_for_core(control),
        _normalized_for_core(candidate),
        receipt,
        git_head=git_head,
    )
    report["execution_binding"] = binding
    report["invocations"] = {
        "control": control_invocation,
        "candidate": candidate_invocation,
    }
    report["by_opponent_seat"] = _strata(report["rows"])

    if report["verdict"] == "UPSIDE_SCREEN":
        bad = {
            name: value
            for name, value in report["by_opponent_seat"].items()
            if (
                value["mean_own_delta"] < 0
                or value["median_own_delta"] < 0
                or value["positive_cells"] < value["negative_cells"]
            )
        }
        if bad:
            report["verdict"] = "SEAT_STRATUM_REGRESSION"
            report["reason"] = (
                "overall upside hides a losing opponent-by-seat stratum: "
                + ", ".join(sorted(bad))
            )
            report["exit_code"] = 1
    return report


def markdown(report: Mapping[str, Any]) -> str:
    text = compare.markdown(report).rstrip()
    strata = report.get("by_opponent_seat")
    if not isinstance(strata, Mapping):
        return text + "\n"
    lines = [
        text,
        "",
        "## Opponent × seat strata",
        "",
        "| Stratum | Cells | Changed | + / 0 / - | Mean own Δ | Median own Δ | Min / max own Δ |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, value in strata.items():
        lines.append(
            f"| {name} | {value['cells']} | {value['changed_cells']} | "
            f"{value['positive_cells']} / {value['zero_cells']} / "
            f"{value['negative_cells']} | {value['mean_own_delta']:+.3f} | "
            f"{value['median_own_delta']:+.3f} | "
            f"{value['minimum_own_delta']:+.3f} / "
            f"{value['maximum_own_delta']:+.3f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--control-wrapper", type=Path, required=True)
    parser.add_argument("--candidate-wrapper", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--opponent", action="append", default=[])
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = compare_bound(
            compare.strict_object(args.control),
            compare.strict_object(args.candidate),
            compare.strict_object(args.receipt),
            compare.strict_object(args.binding),
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
        StrictCompareError,
        compare.CompareError,
        bind_execution.BindingError,
        materialize.MaterializeError,
    ) as exc:
        report = {
            "schema_version": 1,
            "operation": "titan-v2-target-domain-ablation-20260909-sol-bulwark-01",
            "git_head": args.head,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
        }

    compare.atomic_write(
        args.output,
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    compare.atomic_write(args.markdown, markdown(report))
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
