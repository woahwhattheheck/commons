#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticated exact-cell disposition for the TITAN S13 certified prefix.

This successor treats evaluator JSON as untrusted input. Before any actor-emitted
runtime diagnostics can affect a verdict, the report's top-level provenance and
complete cell bank are matched to caller-supplied, byte-authenticated evaluator,
candidate, loader, engine, opponent, seed and timeout inputs. The certified
candidate's composition receipt is also rebound to its runtime and baseline
bytes. Trace divergence remains descriptive only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import certified_report_v2 as v2

SCHEMA = "titan-v3-s13-certified-prefix-report/v3"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
ENGINE_BLOBS = {
    "kaggriculture.py": "3c202c7ee921da239356789e266b694635103fc4",
    "kaggriculture.json": "b354d06b742fe48402513792253f1a5c29366b20",
    "utils.py": "91c8822ee6201ba4a5a8416c7dbe34f95dd61c87",
}
CANONICAL_EVALUATOR_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
DIAGNOSTIC_EVALUATOR_BLOB = "49b493fcd77c8a63b45ce823ff5bed9260b617f8"
PINNED_LOADER_BLOB = "23948e10cfc3d32f46c9abb1321b0d8fc8db21d5"
CERTIFIED_RUNTIME_BLOB = "6bd90321a3eb4a0c3666118426bbb53dbd923312"
DONOR_HEAD = v2.DONOR_HEAD
DONOR_BLOB = v2.DONOR_BLOB


class AuthenticatedReportError(v2.CertifiedReportError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def require_blob(path: Path, expected: str, label: str) -> None:
    actual = git_blob_sha(path)
    if actual != expected:
        raise AuthenticatedReportError(
            f"{label} Git blob drift: expected={expected} actual={actual}"
        )


def parse_spec(value: str) -> tuple[Path | None, str]:
    if value == "official_starter":
        return None, "official_starter"
    path, sep, function = value.partition("::")
    resolved = Path(path).resolve(strict=True)
    return resolved, function if sep else "agent"


def fingerprint_spec(value: str) -> dict[str, Any]:
    path, function = parse_spec(value)
    if path is None:
        return {"entry": "official_starter", "engine_ref": ENGINE_REF}
    return {"entry": path.name, "callable": function, "sha256": sha256(path)}


def parse_opponents(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values:
        label, sep, spec = item.partition("=")
        if not sep or not label or not spec or label in result:
            raise AuthenticatedReportError(
                "each --opponent must be a unique nonempty label=spec"
            )
        result[label] = spec
    if not result:
        raise AuthenticatedReportError("at least one --opponent is required")
    return result


def parse_seeds(value: str) -> list[int]:
    try:
        seeds = [int(piece.strip()) for piece in value.split(",")]
    except ValueError as exc:
        raise AuthenticatedReportError("--seeds must be comma-separated integers") from exc
    if not seeds or len(seeds) != len(set(seeds)):
        raise AuthenticatedReportError("--seeds must be nonempty and distinct")
    return seeds


def authenticated_engine(engine_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, expected_blob in ENGINE_BLOBS.items():
        path = engine_dir / name
        require_blob(path, expected_blob, f"engine source {name}")
        result[name] = sha256(path)
    return result


def expected_report_provenance(
    *,
    evaluator: Path,
    expected_evaluator_blob: str,
    candidate: str,
    loader: Path,
    engine_dir: Path,
    opponents: Mapping[str, str],
    seeds: list[int],
    rng_seed: int,
    action_timeout: float,
    startup_timeout: float,
    game_timeout: float,
    require_recheck: bool,
) -> dict[str, Any]:
    require_blob(evaluator, expected_evaluator_blob, "evaluator")
    require_blob(loader, PINNED_LOADER_BLOB, "loader")
    return {
        "schema_version": 1,
        "engine_ref": ENGINE_REF,
        "engine_sha256": authenticated_engine(engine_dir),
        "loader_sha256": sha256(loader),
        "evaluator_sha256": sha256(evaluator),
        "candidate": fingerprint_spec(candidate),
        "opponents": {label: fingerprint_spec(spec) for label, spec in opponents.items()},
        "seeds": list(seeds),
        "agent_rng_seed": rng_seed,
        "limits": {
            "action_rpc_seconds": float(action_timeout),
            "startup_seconds": float(startup_timeout),
            "game_seconds_between_steps": float(game_timeout),
            "remaining_overage_time": 0,
        },
        "require_recheck": bool(require_recheck),
    }


def _require_equal(report: Mapping[str, Any], key: str, expected: Any, label: str) -> None:
    if report.get(key) != expected:
        raise AuthenticatedReportError(
            f"{label} {key} drift: expected={expected!r} actual={report.get(key)!r}"
        )


def validate_report_provenance(
    report: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    label: str,
    source_seat: int | None = None,
) -> dict[str, Any]:
    """Authenticate top-level evaluator provenance and exact expected cell bank."""
    if not isinstance(report, Mapping):
        raise AuthenticatedReportError(f"{label}: report root is not an object")
    for key in (
        "schema_version", "engine_ref", "engine_sha256", "loader_sha256",
        "evaluator_sha256", "candidate", "opponents", "seeds", "agent_rng_seed",
        "limits",
    ):
        _require_equal(report, key, expected[key], label)

    invocation_id = report.get("invocation_id")
    if (
        not isinstance(invocation_id, str)
        or len(invocation_id) != 32
        or any(ch not in "0123456789abcdef" for ch in invocation_id)
    ):
        raise AuthenticatedReportError(f"{label}: invocation_id is not canonical hex")

    progress = report.get("progress")
    if not isinstance(progress, Mapping):
        raise AuthenticatedReportError(f"{label}: final progress receipt is absent")
    expected_cells = {
        (opponent, seed, seat)
        for opponent in expected["opponents"]
        for seed in expected["seeds"]
        for seat in (0, 1)
    }
    planned = len(expected_cells)
    if (
        progress.get("state") != "complete"
        or progress.get("planned_games") != planned
        or progress.get("recorded_games") != planned
        or progress.get("active_game") is not None
    ):
        raise AuthenticatedReportError(f"{label}: final progress/cell-count receipt drift")

    reproducibility = report.get("reproducibility")
    if expected.get("require_recheck"):
        if (
            not isinstance(reproducibility, Mapping)
            or reproducibility.get("checked") is not True
            or reproducibility.get("same_trace_and_scores") is not True
        ):
            raise AuthenticatedReportError(f"{label}: reproducibility recheck is absent or red")

    games = report.get("games")
    if not isinstance(games, list) or len(games) != planned:
        raise AuthenticatedReportError(f"{label}: game bank cardinality drift")
    observed: set[tuple[str, int, int]] = set()
    for game in games:
        if not isinstance(game, Mapping):
            raise AuthenticatedReportError(f"{label}: game row is not an object")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        key = (opponent, seed, seat)
        if key not in expected_cells or key in observed:
            raise AuthenticatedReportError(f"{label}: unexpected or duplicate game cell {key!r}")
        observed.add(key)
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AuthenticatedReportError(f"{label}: incomplete game at {key!r}")
        steps = game.get("steps")
        episode_steps = game.get("episode_steps")
        if (
            type(steps) is not int or type(episode_steps) is not int
            or steps <= 0 or episode_steps < 2 or steps > episode_steps
        ):
            raise AuthenticatedReportError(f"{label}: invalid executed step interval at {key!r}")
        if source_seat is not None:
            diag = v2.runtime_diagnostics(game, seat)
            if diag["source_seat"] != source_seat:
                raise AuthenticatedReportError(
                    f"{label}: runtime source-seat binding drift at {key!r}"
                )
            for step in diag["activation_steps"]:
                if step >= steps:
                    raise AuthenticatedReportError(
                        f"{label}: activation step {step} lies outside executed [0,{steps}) at {key!r}"
                    )
            handoff = diag.get("handoff_step")
            if handoff is not None and handoff >= steps:
                raise AuthenticatedReportError(
                    f"{label}: handoff step {handoff} lies outside executed [0,{steps}) at {key!r}"
                )
    if observed != expected_cells:
        raise AuthenticatedReportError(f"{label}: exact expected cell bank is incomplete")
    return {"invocation_id": invocation_id, "cells": planned}


def validate_certified_composition(
    *,
    receipt_path: Path,
    candidate_spec: str,
    runtime: Path,
    baseline_entry: Path,
    expected_replay_sha256: str,
    expected_episode: str,
    expected_cutoff: int,
    source_seat: int,
) -> dict[str, Any]:
    receipt = v2.strict_load(receipt_path)
    if not isinstance(receipt, Mapping):
        raise AuthenticatedReportError("certified composition receipt is not an object")
    candidate_path, function = parse_spec(candidate_spec)
    if candidate_path is None or function != "agent":
        raise AuthenticatedReportError("certified candidate must be a concrete ::agent file")
    require_blob(runtime, CERTIFIED_RUNTIME_BLOB, "certified runtime")
    candidate_sha = sha256(candidate_path)
    runtime_sha = sha256(runtime)
    baseline_sha = sha256(baseline_entry)
    checks = {
        "output_python_sha256": candidate_sha,
        "runtime_sha256": runtime_sha,
        "baseline_entry_sha256": baseline_sha,
        "certificate_donor_head": DONOR_HEAD,
        "certificate_donor_blob": DONOR_BLOB,
        "source_seat": source_seat,
        "source_seat_portability": False,
        "prefix_cutoff": expected_cutoff,
        "market_outcome_claim": False,
        "promotion_claim": False,
    }
    for key, expected in checks.items():
        if receipt.get(key) != expected:
            raise AuthenticatedReportError(
                f"certified composition {key} drift: expected={expected!r} actual={receipt.get(key)!r}"
            )
    for key, actual_path in (
        ("output", candidate_path),
        ("runtime", runtime.resolve(strict=True)),
        ("baseline_entry", baseline_entry.resolve(strict=True)),
    ):
        raw = receipt.get(key)
        if not isinstance(raw, str) or Path(raw).resolve() != actual_path:
            raise AuthenticatedReportError(f"certified composition {key} path drift")
    replay = receipt.get("source_replay")
    if not isinstance(replay, Mapping):
        raise AuthenticatedReportError("certified composition source_replay is absent")
    replay_sha = replay.get("sha256") or replay.get("source_sha256")
    replay_episode = replay.get("episode") or replay.get("episode_id")
    if replay_sha != expected_replay_sha256:
        raise AuthenticatedReportError("certified composition replay digest drift")
    if str(replay_episode) != str(expected_episode):
        raise AuthenticatedReportError("certified composition replay episode drift")
    return {
        "receipt_sha256": sha256(receipt_path),
        "candidate_sha256": candidate_sha,
        "runtime_sha256": runtime_sha,
        "runtime_git_blob": CERTIFIED_RUNTIME_BLOB,
        "baseline_entry_sha256": baseline_sha,
        "source_replay_sha256": expected_replay_sha256,
        "source_episode": str(expected_episode),
        "prefix_cutoff": expected_cutoff,
    }


def build_report(
    *,
    control_path: Path,
    unsafe_path: Path,
    certified_path: Path,
    control_expected: Mapping[str, Any],
    unsafe_expected: Mapping[str, Any],
    certified_expected: Mapping[str, Any],
    certified_composition: Mapping[str, Any],
    source_seat: int,
) -> dict[str, Any]:
    control_raw = v2.strict_load(control_path)
    unsafe_raw = v2.strict_load(unsafe_path)
    certified_raw = v2.strict_load(certified_path)
    control_auth = validate_report_provenance(control_raw, control_expected, label="control")
    unsafe_auth = validate_report_provenance(unsafe_raw, unsafe_expected, label="unsafe_prefix")
    certified_auth = validate_report_provenance(
        certified_raw,
        certified_expected,
        label="certified_prefix",
        source_seat=source_seat,
    )
    ids = {
        control_auth["invocation_id"],
        unsafe_auth["invocation_id"],
        certified_auth["invocation_id"],
    }
    if len(ids) != 3:
        raise AuthenticatedReportError("arm invocation ids must be distinct")

    report = v2.build_report(
        control_path,
        unsafe_path,
        certified_path,
        source_seat=source_seat,
    )
    report["schema"] = SCHEMA
    provenance = {
        "control_report_sha256": sha256(control_path),
        "unsafe_report_sha256": sha256(unsafe_path),
        "certified_report_sha256": sha256(certified_path),
        "control": control_auth,
        "unsafe_prefix": unsafe_auth,
        "certified_prefix": certified_auth,
        "engine_ref": ENGINE_REF,
        "engine_sha256": certified_expected["engine_sha256"],
        "loader_sha256": certified_expected["loader_sha256"],
        "control_evaluator_sha256": control_expected["evaluator_sha256"],
        "unsafe_evaluator_sha256": unsafe_expected["evaluator_sha256"],
        "certified_evaluator_sha256": certified_expected["evaluator_sha256"],
        "control_candidate": control_expected["candidate"],
        "unsafe_candidate": unsafe_expected["candidate"],
        "certified_candidate": certified_expected["candidate"],
        "opponents": certified_expected["opponents"],
        "seeds": certified_expected["seeds"],
        "agent_rng_seed": certified_expected["agent_rng_seed"],
        "limits": certified_expected["limits"],
        "certified_composition": dict(certified_composition),
    }
    provenance["sha256"] = hashlib.sha256(v2.canonical(provenance)).hexdigest()
    report["authenticated_provenance"] = provenance
    report["scope"] = (
        "reused frozen-seed research only; evaluator/candidate/dependency/engine/loader/"
        "opponent/seed/cell provenance authenticated before runtime diagnostics; activation derives "
        "only from retained in-range runtime emissions; no promotion, provider, Kaggle, or submission mutation"
    )
    return report


def _finite_positive(value: float, name: str) -> float:
    if not math.isfinite(value) or value <= 0:
        raise AuthenticatedReportError(f"{name} must be finite and positive")
    return float(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--unsafe-prefix", type=Path, required=True)
    parser.add_argument("--certified-prefix", type=Path, required=True)
    parser.add_argument("--control-evaluator", type=Path, required=True)
    parser.add_argument("--unsafe-evaluator", type=Path, required=True)
    parser.add_argument("--certified-evaluator", type=Path, required=True)
    parser.add_argument("--control-candidate", required=True)
    parser.add_argument("--unsafe-candidate", required=True)
    parser.add_argument("--certified-candidate", required=True)
    parser.add_argument("--certified-receipt", type=Path, required=True)
    parser.add_argument("--certified-runtime", type=Path, required=True)
    parser.add_argument("--certified-baseline-entry", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--opponent", action="append", default=[])
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--rng-seed", type=int, required=True)
    parser.add_argument("--action-timeout", type=float, required=True)
    parser.add_argument("--startup-timeout", type=float, required=True)
    parser.add_argument("--game-timeout", type=float, required=True)
    parser.add_argument("--require-recheck", action="store_true")
    parser.add_argument("--source-seat", type=int, required=True)
    parser.add_argument("--expected-source-replay-sha256", required=True)
    parser.add_argument("--expected-source-episode", required=True)
    parser.add_argument("--expected-prefix-cutoff", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.source_seat not in (0, 1):
        raise AuthenticatedReportError("source seat must be 0 or 1")
    opponents = parse_opponents(args.opponent)
    seeds = parse_seeds(args.seeds)
    action_timeout = _finite_positive(args.action_timeout, "action timeout")
    startup_timeout = _finite_positive(args.startup_timeout, "startup timeout")
    game_timeout = _finite_positive(args.game_timeout, "game timeout")
    common = dict(
        loader=args.loader.resolve(strict=True),
        engine_dir=args.engine_dir.resolve(strict=True),
        opponents=opponents,
        seeds=seeds,
        rng_seed=args.rng_seed,
        action_timeout=action_timeout,
        startup_timeout=startup_timeout,
        game_timeout=game_timeout,
        require_recheck=args.require_recheck,
    )
    control_expected = expected_report_provenance(
        evaluator=args.control_evaluator.resolve(strict=True),
        expected_evaluator_blob=CANONICAL_EVALUATOR_BLOB,
        candidate=args.control_candidate,
        **common,
    )
    unsafe_expected = expected_report_provenance(
        evaluator=args.unsafe_evaluator.resolve(strict=True),
        expected_evaluator_blob=CANONICAL_EVALUATOR_BLOB,
        candidate=args.unsafe_candidate,
        **common,
    )
    certified_expected = expected_report_provenance(
        evaluator=args.certified_evaluator.resolve(strict=True),
        expected_evaluator_blob=DIAGNOSTIC_EVALUATOR_BLOB,
        candidate=args.certified_candidate,
        **common,
    )
    composition = validate_certified_composition(
        receipt_path=args.certified_receipt.resolve(strict=True),
        candidate_spec=args.certified_candidate,
        runtime=args.certified_runtime.resolve(strict=True),
        baseline_entry=args.certified_baseline_entry.resolve(strict=True),
        expected_replay_sha256=args.expected_source_replay_sha256,
        expected_episode=args.expected_source_episode,
        expected_cutoff=args.expected_prefix_cutoff,
        source_seat=args.source_seat,
    )
    report = build_report(
        control_path=args.control,
        unsafe_path=args.unsafe_prefix,
        certified_path=args.certified_prefix,
        control_expected=control_expected,
        unsafe_expected=unsafe_expected,
        certified_expected=certified_expected,
        certified_composition=composition,
        source_seat=args.source_seat,
    )
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(v2.markdown(report), encoding="utf-8")
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except v2.CertifiedReportError as exc:
        print(f"ERROR: {exc}", file=__import__('sys').stderr)
        raise SystemExit(2)
