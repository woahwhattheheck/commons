# SPDX-License-Identifier: Apache-2.0
"""Fail-closed binding of the frozen Titan v3 policy to retained game ledgers."""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping

from snapshot_model import EvidenceLedgerPin, Pin, SnapshotError, sha256

EXPECTED_ENGINE_REFERENCE = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_ENGINE_SHA256 = {
    "kaggriculture.py": "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e",
    "kaggriculture.json": "a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867",
    "utils.py": "537b627b11784d424147ef57ebb0369b039bf83c9f891e81f10486b1f552334b",
}
EXPECTED_EVALUATOR_SHA256 = "e30b3108e0027477ab7ddbc057892a241c41a1f2b38f72caf267477877c4333c"
EXPECTED_BENCHMARK_SHA256 = "30c8f056d766e14af3ffba9638364358c812b5e3764749d63b12e6f70cd3d99d"
EXPECTED_STEPS = 719
EXPECTED_EPISODE_STEPS = 720


def _reject_constant(value: str) -> None:
    raise SnapshotError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _decode_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except SnapshotError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"invalid JSON evidence {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise SnapshotError(f"JSON evidence must be an object: {label}")
    return value


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SnapshotError(f"cannot read evidence {label}: {exc}") from exc


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise SnapshotError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise SnapshotError(f"{label} must be an array")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SnapshotError(f"{label} must be a nonempty string")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SnapshotError(f"{label} must be an integer")
    return value


def _boolean(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise SnapshotError(f"{label} must be a boolean")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SnapshotError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise SnapshotError(f"{label} must be a finite number")
    return result


def _outcome(own: float, rival: float) -> str:
    return "W" if own > rival else "L" if own < rival else "T"


def _source_identity(document: Mapping[str, Any], source: Pin, label: str) -> None:
    freeze = _mapping(document.get("freeze"), f"{label}.freeze")
    if freeze.get("version") != source.source_freeze_version:
        raise SnapshotError(f"{label} freeze version does not bind the source archive")
    frozen = _mapping(freeze.get("files"), f"{label}.freeze.files")
    for name, expected in source.frozen_hashes.items():
        if frozen.get(name) != expected:
            raise SnapshotError(f"{label} source identity mismatch: {name}")

    runtime = _mapping(document.get("runtime_manifest"), f"{label}.runtime_manifest")
    targets = _mapping(runtime.get("targets"), f"{label}.runtime_manifest.targets")
    candidate = _mapping(targets.get("candidate"), f"{label}.runtime_manifest.targets.candidate")
    if candidate.get("sha256") != source.frozen_hashes["candidate.py"]:
        raise SnapshotError(f"{label} executed candidate entrypoint does not match the frozen source")
    sources = _mapping(runtime.get("lane_python_sources"), f"{label}.runtime_manifest.lane_python_sources")
    for name in ("scheduler.py", "candidate.py", "mechanics.py"):
        record = _mapping(sources.get(name), f"{label}.runtime_manifest.lane_python_sources.{name}")
        if record.get("sha256") != source.frozen_hashes[name]:
            raise SnapshotError(f"{label} executed source mismatch: {name}")


def _environment_identity(document: Mapping[str, Any], label: str) -> dict[str, Any]:
    if document.get("engine_reference") != EXPECTED_ENGINE_REFERENCE:
        raise SnapshotError(f"{label} engine reference mismatch")
    engine = _mapping(document.get("engine_sha256"), f"{label}.engine_sha256")
    if dict(engine) != EXPECTED_ENGINE_SHA256:
        raise SnapshotError(f"{label} engine closure mismatch")
    if document.get("evaluator_sha256") != EXPECTED_EVALUATOR_SHA256:
        raise SnapshotError(f"{label} evaluator mismatch")
    if document.get("benchmark_sha256") != EXPECTED_BENCHMARK_SHA256:
        raise SnapshotError(f"{label} benchmark/opponent bundle mismatch")
    return {
        "engine_reference": EXPECTED_ENGINE_REFERENCE,
        "engine_sha256": dict(EXPECTED_ENGINE_SHA256),
        "evaluator_sha256": EXPECTED_EVALUATOR_SHA256,
        "benchmark_sha256": EXPECTED_BENCHMARK_SHA256,
    }


def _validate_games(document: Mapping[str, Any], pin: EvidenceLedgerPin) -> tuple[dict[tuple[str, int, str, int], dict[str, Any]], dict[str, dict[str, int]]]:
    expected = set(itertools.product(pin.variants, pin.seeds, pin.opponents, (0, 1)))
    found: dict[tuple[str, int, str, int], dict[str, Any]] = {}
    counts = {variant: {"W": 0, "T": 0, "L": 0, "failed": 0, "games": 0} for variant in pin.variants}

    for index, raw in enumerate(_list(document.get("games"), f"{pin.name}.games")):
        row = _mapping(raw, f"{pin.name}.games[{index}]")
        variant = _text(row.get("variant"), f"{pin.name}.games[{index}].variant")
        seed = _integer(row.get("seed"), f"{pin.name}.games[{index}].seed")
        opponent = _text(row.get("opponent"), f"{pin.name}.games[{index}].opponent")
        seat = _integer(row.get("candidate_seat"), f"{pin.name}.games[{index}].candidate_seat")
        key = (variant, seed, opponent, seat)
        if key not in expected:
            raise SnapshotError(f"{pin.name} contains an unexpected cell: {key}")
        if key in found:
            raise SnapshotError(f"{pin.name} contains a duplicate cell: {key}")
        if row.get("status") != "complete" or row.get("failure") is not None:
            raise SnapshotError(f"{pin.name} cell is not complete: {key}")
        if _integer(row.get("steps"), f"{pin.name}.{key}.steps") != EXPECTED_STEPS:
            raise SnapshotError(f"{pin.name} cell has the wrong decision count: {key}")
        if _integer(row.get("episode_steps"), f"{pin.name}.{key}.episode_steps") != EXPECTED_EPISODE_STEPS:
            raise SnapshotError(f"{pin.name} cell has the wrong episode length: {key}")

        scores = _list(row.get("scores"), f"{pin.name}.{key}.scores")
        if len(scores) != 2:
            raise SnapshotError(f"{pin.name} cell must contain exactly two scores: {key}")
        score0 = _finite(scores[0], f"{pin.name}.{key}.scores[0]")
        score1 = _finite(scores[1], f"{pin.name}.{key}.scores[1]")
        own = _finite(row.get("own_final_cash"), f"{pin.name}.{key}.own_final_cash")
        rival = _finite(row.get("rival_final_cash"), f"{pin.name}.{key}.rival_final_cash")
        if (own, rival) != ((score0, score1) if seat == 0 else (score1, score0)):
            raise SnapshotError(f"{pin.name} cell score/seat binding mismatch: {key}")
        outcome = _outcome(own, rival)
        if row.get("outcome") != outcome:
            raise SnapshotError(f"{pin.name} cell outcome mismatch: {key}")

        clean = dict(row)
        clean["own_final_cash"] = own
        clean["rival_final_cash"] = rival
        clean["outcome"] = outcome
        found[key] = clean
        counts[variant][outcome] += 1
        counts[variant]["games"] += 1

    missing = sorted(expected - set(found))
    if missing:
        raise SnapshotError(f"{pin.name} is missing required cells: {missing}")

    summary = _mapping(document.get("summary"), f"{pin.name}.summary")
    reported = _mapping(summary.get("W_T_L_first"), f"{pin.name}.summary.W_T_L_first")
    for variant, derived in counts.items():
        variant_report = _mapping(reported.get(variant), f"{pin.name}.summary.W_T_L_first.{variant}")
        for field, value in derived.items():
            actual = _integer(variant_report.get(field), f"{pin.name}.summary.{variant}.{field}")
            if actual != value:
                raise SnapshotError(f"{pin.name} summary mismatch: {variant}.{field}")
    return found, counts


def _validate_pairs(document: Mapping[str, Any], pin: EvidenceLedgerPin, rows: Mapping[tuple[str, int, str, int], Mapping[str, Any]]) -> dict[str, Any] | None:
    summary = _mapping(document.get("summary"), f"{pin.name}.summary")
    reported_pairs = _list(summary.get("paired_outcomes"), f"{pin.name}.summary.paired_outcomes")
    if set(pin.variants) != {"baseline", "candidate"}:
        if reported_pairs:
            raise SnapshotError(f"{pin.name} must not report paired outcomes without both variants")
        return None

    expected_keys = set(itertools.product(pin.seeds, pin.opponents, (0, 1)))
    derived: dict[tuple[int, str, int], dict[str, Any]] = {}
    deltas: list[float] = []
    for seed, opponent, seat in sorted(expected_keys):
        baseline = rows[("baseline", seed, opponent, seat)]
        candidate = rows[("candidate", seed, opponent, seat)]
        own_delta = candidate["own_final_cash"] - baseline["own_final_cash"]
        rival_delta = candidate["rival_final_cash"] - baseline["rival_final_cash"]
        derived[(seed, opponent, seat)] = {
            "variant": "candidate",
            "seed": seed,
            "opponent": opponent,
            "seat": seat,
            "baseline": baseline["outcome"],
            "candidate": candidate["outcome"],
            "flipped": baseline["outcome"] != candidate["outcome"],
            "own_cash_delta": own_delta,
            "rival_cash_delta": rival_delta,
        }
        deltas.append(own_delta)

    reported: dict[tuple[int, str, int], Mapping[str, Any]] = {}
    for index, raw in enumerate(reported_pairs):
        row = _mapping(raw, f"{pin.name}.summary.paired_outcomes[{index}]")
        key = (
            _integer(row.get("seed"), f"{pin.name}.paired[{index}].seed"),
            _text(row.get("opponent"), f"{pin.name}.paired[{index}].opponent"),
            _integer(row.get("seat"), f"{pin.name}.paired[{index}].seat"),
        )
        if key not in expected_keys or key in reported:
            raise SnapshotError(f"{pin.name} paired outcome key is missing, duplicate, or unexpected: {key}")
        reported[key] = row
    if set(reported) != expected_keys:
        raise SnapshotError(f"{pin.name} paired outcome set is incomplete")
    for key, expected_row in derived.items():
        actual = reported[key]
        for field, value in expected_row.items():
            actual_value = actual.get(field)
            if isinstance(value, bool):
                actual_value = _boolean(actual_value, f"{pin.name}.paired.{key}.{field}")
            elif isinstance(value, float):
                actual_value = _finite(actual_value, f"{pin.name}.paired.{key}.{field}")
            if actual_value != value:
                raise SnapshotError(f"{pin.name} paired outcome mismatch: {key}.{field}")

    negative = sum(delta < 0 for delta in deltas)
    positive = sum(delta > 0 for delta in deltas)
    return {
        "cells": len(deltas),
        "sum_own_cash_delta": sum(deltas),
        "mean_own_cash_delta": fmean(deltas),
        "minimum_own_cash_delta": min(deltas),
        "maximum_own_cash_delta": max(deltas),
        "positive_cells": positive,
        "zero_cells": len(deltas) - positive - negative,
        "negative_cells": negative,
        "uniform_non_regression": negative == 0,
    }


def validate_evidence(lab_root: Path, source: Pin) -> dict[str, Any]:
    """Bind exact source bytes to complete, immutable, semantically checked result ledgers."""
    if not source.evidence_ledgers:
        raise SnapshotError("source pin has no evidence-ledger contract")
    manifest_path = lab_root / "exports" / "FILES.json"
    manifest = _decode_object(_read_bytes(manifest_path, "exports/FILES.json"), "exports/FILES.json")
    environment: dict[str, Any] | None = None
    result: dict[str, Any] = {}

    names = [pin.name for pin in source.evidence_ledgers]
    if len(names) != len(set(names)):
        raise SnapshotError("source pin contains duplicate evidence-ledger names")
    if set(names) != {"development", "held_out"}:
        raise SnapshotError("source pin must bind exactly development and held_out ledgers")

    for ledger_pin in source.evidence_ledgers:
        path = lab_root / ledger_pin.path
        payload = _read_bytes(path, ledger_pin.path)
        if len(payload) != ledger_pin.bytes:
            raise SnapshotError(f"{ledger_pin.name} ledger byte count drift")
        digest = sha256(payload)
        if digest != ledger_pin.sha256:
            raise SnapshotError(f"{ledger_pin.name} ledger SHA-256 drift")
        if manifest.get(ledger_pin.path) != {"bytes": ledger_pin.bytes, "sha256": ledger_pin.sha256}:
            raise SnapshotError(f"FILES.json does not bind {ledger_pin.path}")

        document = _decode_object(payload, ledger_pin.path)
        _source_identity(document, source, ledger_pin.name)
        current_environment = _environment_identity(document, ledger_pin.name)
        if environment is None:
            environment = current_environment
        elif current_environment != environment:
            raise SnapshotError("evidence ledgers do not share one execution environment")
        rows, counts = _validate_games(document, ledger_pin)
        paired = _validate_pairs(document, ledger_pin, rows)
        candidate = counts.get("candidate")
        if candidate is None:
            raise SnapshotError(f"{ledger_pin.name} does not contain a candidate variant")
        entry: dict[str, Any] = {
            "ledger": {"path": ledger_pin.path, "bytes": ledger_pin.bytes, "sha256": ledger_pin.sha256},
            "seeds": list(ledger_pin.seeds),
            "opponents": list(ledger_pin.opponents),
            "seats": [0, 1],
            "candidate": dict(candidate),
        }
        if "baseline" in counts:
            entry["baseline"] = dict(counts["baseline"])
        if paired is not None:
            entry["paired"] = paired
        result[ledger_pin.name] = entry

    held = result.get("held_out")
    if not isinstance(held, dict) or not isinstance(held.get("paired"), dict):
        raise SnapshotError("held_out paired control evidence is required")
    paired = held["paired"]
    development = result.get("development")
    if not isinstance(development, dict):
        raise SnapshotError("development control evidence is required")
    development_candidate = _mapping(development.get("candidate"), "development.candidate")
    held_candidate = _mapping(held.get("candidate"), "held_out.candidate")
    strong_control = all(
        record.get("W") == record.get("games") and record.get("L") == 0 and record.get("failed") == 0
        for record in (development_candidate, held_candidate)
    )
    return {
        "status": "BOUND_CONTROL_ONLY",
        "source": {
            "commit": source.source_commit,
            "scheduler_sha256": source.frozen_hashes["scheduler.py"],
            "candidate_sha256": source.frozen_hashes["candidate.py"],
        },
        "environment": environment,
        **result,
        "strength_boundary": {
            "strong_measured_control": strong_control,
            "uniform_non_regression": paired["uniform_non_regression"],
            "historical_local_only": True,
            "hosted_leaderboard_claim": False,
            "promotion": "FULL_CURRENT_MATCHED_PANEL_REQUIRED",
        },
    }
