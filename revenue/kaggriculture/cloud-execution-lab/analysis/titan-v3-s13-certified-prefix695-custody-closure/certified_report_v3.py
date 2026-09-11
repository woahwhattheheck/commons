#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticated wrapper for the S13 exact-cell report.

The v2 report owns the paired-score and scientific-verdict math.  This wrapper
fails closed on evaluator/candidate/engine/opponent/seed provenance and on
runtime activation steps which were not actually executed before delegating to
that reviewed math.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from itertools import product
from pathlib import Path
from typing import Any, Mapping, Sequence

import certified_report_v2 as v2

SCHEMA = "titan-v3-s13-certified-prefix-report/v3"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
HERE = Path(__file__).resolve().parent
BASE_EVALUATOR = HERE.parents[2] / "cloud-eval" / "evaluate.py"
DIAGNOSTIC_EVALUATOR = HERE / "diagnostic_evaluate.py"


class AuthenticatedReportError(v2.CertifiedReportError):
    pass


def sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise AuthenticatedReportError(f"cannot hash required source {path}: {exc}") from exc


def _digest(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise AuthenticatedReportError(f"{label} is not a lowercase SHA-256 digest")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AuthenticatedReportError(f"{label} is not an object")
    return value


def _candidate_sha(report: Mapping[str, Any], label: str) -> str:
    candidate = _mapping(report.get("candidate"), f"{label} candidate fingerprint")
    return _digest(candidate.get("sha256"), f"{label} candidate sha256")


def _engine_hashes(report: Mapping[str, Any], label: str) -> Mapping[str, Any]:
    hashes = _mapping(report.get("engine_sha256"), f"{label} engine_sha256")
    if not hashes:
        raise AuthenticatedReportError(f"{label} engine_sha256 is empty")
    for name, value in hashes.items():
        if not isinstance(name, str) or not name:
            raise AuthenticatedReportError(f"{label} engine hash name is malformed")
        _digest(value, f"{label} engine_sha256[{name!r}]")
    return hashes


def _game_bank(
    report: Mapping[str, Any],
    label: str,
) -> dict[tuple[str, int, int], Mapping[str, Any]]:
    games = report.get("games")
    if not isinstance(games, list):
        raise AuthenticatedReportError(f"{label} evaluator report has no games")
    result: dict[tuple[str, int, int], Mapping[str, Any]] = {}
    for game in games:
        if not isinstance(game, Mapping):
            raise AuthenticatedReportError(f"{label} evaluator game is malformed")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if not isinstance(opponent, str) or not opponent or type(seed) is not int or seat not in (0, 1):
            raise AuthenticatedReportError(f"{label} evaluator cell key is malformed")
        steps = game.get("steps")
        episode_steps = game.get("episode_steps")
        if (
            type(steps) is not int
            or type(episode_steps) is not int
            or steps < 0
            or episode_steps <= 0
            or steps > episode_steps
        ):
            raise AuthenticatedReportError(f"{label} executed-step bounds are malformed")
        key = (opponent, seed, seat)
        if key in result:
            raise AuthenticatedReportError(f"{label} duplicate evaluator cell: {key!r}")
        result[key] = game
    return result


def _validate_report(
    report: Any,
    *,
    label: str,
    expected_evaluator_sha256: str,
    expected_candidate_sha256: str,
    expected_seeds: tuple[int, ...],
    expected_opponents: tuple[str, ...],
) -> tuple[Mapping[str, Any], dict[tuple[str, int, int], Mapping[str, Any]]]:
    report = _mapping(report, f"{label} evaluator report")
    if report.get("schema_version") != 1:
        raise AuthenticatedReportError(f"{label} evaluator schema_version drift")
    if report.get("engine_ref") != ENGINE_REF:
        raise AuthenticatedReportError(f"{label} engine_ref drift")
    _engine_hashes(report, label)
    _digest(report.get("loader_sha256"), f"{label} loader_sha256")
    if _digest(report.get("evaluator_sha256"), f"{label} evaluator_sha256") != expected_evaluator_sha256:
        raise AuthenticatedReportError(f"{label} evaluator_sha256 drift")
    if _candidate_sha(report, label) != expected_candidate_sha256:
        raise AuthenticatedReportError(f"{label} candidate sha256 drift")

    seeds = report.get("seeds")
    if (
        not isinstance(seeds, list)
        or any(type(seed) is not int for seed in seeds)
        or tuple(seeds) != expected_seeds
        or len(set(seeds)) != len(seeds)
    ):
        raise AuthenticatedReportError(f"{label} seed bank drift")

    opponents = _mapping(report.get("opponents"), f"{label} opponent fingerprints")
    if tuple(sorted(opponents)) != tuple(sorted(expected_opponents)):
        raise AuthenticatedReportError(f"{label} opponent bank drift")
    for name, fingerprint in opponents.items():
        _mapping(fingerprint, f"{label} opponent fingerprint {name!r}")

    if type(report.get("agent_rng_seed")) is not int:
        raise AuthenticatedReportError(f"{label} agent_rng_seed is malformed")
    if not isinstance(report.get("python"), str) or not report["python"]:
        raise AuthenticatedReportError(f"{label} python provenance is absent")
    if not isinstance(report.get("platform"), str) or not report["platform"]:
        raise AuthenticatedReportError(f"{label} platform provenance is absent")
    _mapping(report.get("limits"), f"{label} limits")
    if not isinstance(report.get("method"), str) or not report["method"]:
        raise AuthenticatedReportError(f"{label} method provenance is absent")

    games = _game_bank(report, label)
    expected_cells = set(product(expected_opponents, expected_seeds, (0, 1)))
    if set(games) != expected_cells:
        missing = sorted(expected_cells - set(games))
        extra = sorted(set(games) - expected_cells)
        raise AuthenticatedReportError(
            f"{label} evaluator cell bank drift: missing={missing!r} extra={extra!r}"
        )
    return report, games


def _shared_provenance(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "engine_ref": report["engine_ref"],
        "engine_sha256": report["engine_sha256"],
        "loader_sha256": report["loader_sha256"],
        "opponents": report["opponents"],
        "seeds": report["seeds"],
        "agent_rng_seed": report["agent_rng_seed"],
        "python": report["python"],
        "platform": report["platform"],
        "limits": report["limits"],
        "method": report["method"],
    }


def _validate_activation_bounds(
    certified_games: Mapping[tuple[str, int, int], Mapping[str, Any]],
) -> None:
    for key, game in certified_games.items():
        seat = game["candidate_seat"]
        actors = game.get("actors")
        if not isinstance(actors, list) or len(actors) != 2 or not isinstance(actors[seat], Mapping):
            raise AuthenticatedReportError(f"certified actor diagnostics are malformed at {key!r}")
        diagnostics = actors[seat].get("agent_diagnostics")
        if not isinstance(diagnostics, Mapping):
            raise AuthenticatedReportError(f"certified runtime diagnostics are absent at {key!r}")
        activation_steps = diagnostics.get("activation_steps")
        if not isinstance(activation_steps, list) or any(type(step) is not int for step in activation_steps):
            raise AuthenticatedReportError(f"certified activation_steps are malformed at {key!r}")
        executed_steps = game["steps"]
        if any(step < 0 or step >= executed_steps for step in activation_steps):
            raise AuthenticatedReportError(
                f"certified activation step outside executed interval at {key!r}: "
                f"steps={executed_steps} activation_steps={activation_steps!r}"
            )


def validate_provenance(
    control_path: Path,
    unsafe_path: Path,
    certified_path: Path,
    *,
    expected_control_candidate_sha256: str,
    expected_unsafe_candidate_sha256: str,
    expected_certified_candidate_sha256: str,
    expected_seeds: Sequence[int],
    expected_opponents: Sequence[str],
) -> dict[str, Any]:
    seeds = tuple(expected_seeds)
    opponents = tuple(expected_opponents)
    if not seeds or any(type(seed) is not int for seed in seeds) or len(set(seeds)) != len(seeds):
        raise AuthenticatedReportError("expected seed bank is malformed")
    if (
        not opponents
        or any(not isinstance(name, str) or not name for name in opponents)
        or len(set(opponents)) != len(opponents)
    ):
        raise AuthenticatedReportError("expected opponent bank is malformed")

    expected_control_candidate_sha256 = _digest(
        expected_control_candidate_sha256, "expected control candidate sha256"
    )
    expected_unsafe_candidate_sha256 = _digest(
        expected_unsafe_candidate_sha256, "expected unsafe candidate sha256"
    )
    expected_certified_candidate_sha256 = _digest(
        expected_certified_candidate_sha256, "expected certified candidate sha256"
    )
    base_evaluator_sha256 = sha256(BASE_EVALUATOR)
    diagnostic_evaluator_sha256 = sha256(DIAGNOSTIC_EVALUATOR)

    control, control_games = _validate_report(
        v2.strict_load(control_path),
        label="control",
        expected_evaluator_sha256=base_evaluator_sha256,
        expected_candidate_sha256=expected_control_candidate_sha256,
        expected_seeds=seeds,
        expected_opponents=opponents,
    )
    unsafe, unsafe_games = _validate_report(
        v2.strict_load(unsafe_path),
        label="unsafe",
        expected_evaluator_sha256=base_evaluator_sha256,
        expected_candidate_sha256=expected_unsafe_candidate_sha256,
        expected_seeds=seeds,
        expected_opponents=opponents,
    )
    certified, certified_games = _validate_report(
        v2.strict_load(certified_path),
        label="certified",
        expected_evaluator_sha256=diagnostic_evaluator_sha256,
        expected_candidate_sha256=expected_certified_candidate_sha256,
        expected_seeds=seeds,
        expected_opponents=opponents,
    )

    shared = _shared_provenance(control)
    if _shared_provenance(unsafe) != shared or _shared_provenance(certified) != shared:
        raise AuthenticatedReportError("paired evaluator provenance differs across arms")
    if set(control_games) != set(unsafe_games) or set(control_games) != set(certified_games):
        raise AuthenticatedReportError("paired evaluator cell banks differ")
    _validate_activation_bounds(certified_games)

    cell_keys = [list(key) for key in sorted(control_games)]
    provenance = {
        "base_evaluator_sha256": base_evaluator_sha256,
        "diagnostic_evaluator_sha256": diagnostic_evaluator_sha256,
        "control_candidate_sha256": expected_control_candidate_sha256,
        "unsafe_candidate_sha256": expected_unsafe_candidate_sha256,
        "certified_candidate_sha256": expected_certified_candidate_sha256,
        "shared": shared,
        "cell_keys": cell_keys,
    }
    provenance["sha256"] = hashlib.sha256(v2.canonical(provenance)).hexdigest()
    return provenance


def build_report(
    control_path: Path,
    unsafe_path: Path,
    certified_path: Path,
    *,
    source_seat: int,
    expected_control_candidate_sha256: str,
    expected_unsafe_candidate_sha256: str,
    expected_certified_candidate_sha256: str,
    expected_seeds: Sequence[int],
    expected_opponents: Sequence[str],
) -> dict[str, Any]:
    provenance = validate_provenance(
        control_path,
        unsafe_path,
        certified_path,
        expected_control_candidate_sha256=expected_control_candidate_sha256,
        expected_unsafe_candidate_sha256=expected_unsafe_candidate_sha256,
        expected_certified_candidate_sha256=expected_certified_candidate_sha256,
        expected_seeds=expected_seeds,
        expected_opponents=expected_opponents,
    )
    report = v2.build_report(
        control_path,
        unsafe_path,
        certified_path,
        source_seat=source_seat,
    )
    report["schema"] = SCHEMA
    report["authenticated_provenance"] = provenance
    report["scope"] = (
        "reused frozen seeds only; runtime activation is accepted only from an exact "
        "diagnostic-evaluator/candidate/engine/opponent/seed/cell binding and only for "
        "executed steps; no promotion, provider, Kaggle, or submission mutation"
    )
    return report


def markdown(report: Mapping[str, Any]) -> str:
    lines = v2.markdown(report).splitlines()
    if lines:
        lines[0] = "# TITAN V3 S13 authenticated exact-certified prefix-695 report"
    insert_at = 7 if len(lines) >= 7 else len(lines)
    lines[insert_at:insert_at] = [
        f"**Authenticated provenance SHA-256:** `{report['authenticated_provenance']['sha256']}`",
        "",
    ]
    return "\n".join(lines) + "\n"


def _csv_ints(value: str) -> list[int]:
    try:
        result = [int(item) for item in value.split(",") if item]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc
    if not result:
        raise argparse.ArgumentTypeError("expected at least one integer")
    return result


def _csv_strings(value: str) -> list[str]:
    result = [item for item in value.split(",") if item]
    if not result:
        raise argparse.ArgumentTypeError("expected at least one value")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--unsafe-prefix", type=Path, required=True)
    parser.add_argument("--certified-prefix", type=Path, required=True)
    parser.add_argument("--source-seat", type=int, required=True)
    parser.add_argument("--expected-control-candidate-sha256", required=True)
    parser.add_argument("--expected-unsafe-candidate-sha256", required=True)
    parser.add_argument("--expected-certified-candidate-sha256", required=True)
    parser.add_argument("--expected-seeds", type=_csv_ints, required=True)
    parser.add_argument("--expected-opponents", type=_csv_strings, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(
        args.control,
        args.unsafe_prefix,
        args.certified_prefix,
        source_seat=args.source_seat,
        expected_control_candidate_sha256=args.expected_control_candidate_sha256,
        expected_unsafe_candidate_sha256=args.expected_unsafe_candidate_sha256,
        expected_certified_candidate_sha256=args.expected_certified_candidate_sha256,
        expected_seeds=args.expected_seeds,
        expected_opponents=args.expected_opponents,
    )
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
