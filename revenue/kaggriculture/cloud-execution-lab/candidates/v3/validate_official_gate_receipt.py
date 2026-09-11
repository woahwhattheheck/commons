#!/usr/bin/env python3
"""Validate whether a TITAN V3.1 simulation receipt qualifies as an official gate.

This is evidence/tooling only. It does not execute Kaggriculture, mutate a candidate,
or decide whether an economically valid result should be promoted.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


class ReceiptError(ValueError):
    """Raised when a claimed gate receipt is incomplete, ambiguous, or inconsistent."""


RECEIPT_SCHEMA = "titan-v31-gate-receipt/v1"
OFFICIAL_INTERPRETER_COMMIT = "28b6d8af3"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReceiptError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ReceiptError(f"{label} must be a list")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ReceiptError(f"{label} must be a lowercase 64-hex SHA-256")
    return value


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReceiptError(f"{label} must be a JSON number")
    out = float(value)
    if not math.isfinite(out):
        raise ReceiptError(f"{label} must be finite")
    return out


def _seat(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
        raise ReceiptError(f"{label} must be 0 or 1")
    return value


def _score_pair(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise ReceiptError(f"{label} must contain [seat0, seat1]")
    return _number(value[0], f"{label}[0]"), _number(value[1], f"{label}[1]")


def _latest_release(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    releases = manifest.get("releases")
    if not isinstance(releases, list) or not releases:
        raise ReceiptError("manifest.releases must be a non-empty list")
    return _mapping(releases[-1], "manifest.releases[-1]")


def _expected_cells(panel: Mapping[str, Any]) -> set[tuple[int, int]]:
    seeds = _list(panel.get("seeds"), "panel.seeds")
    seats = _list(panel.get("seats"), "panel.seats")
    if not seeds:
        raise ReceiptError("panel.seeds must be non-empty")
    normalized_seeds: list[int] = []
    for idx, seed in enumerate(seeds):
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ReceiptError(f"panel.seeds[{idx}] must be an integer")
        normalized_seeds.append(seed)
    normalized_seats = [_seat(seat, f"panel.seats[{idx}]") for idx, seat in enumerate(seats)]
    if sorted(set(normalized_seats)) != [0, 1] or len(normalized_seats) != 2:
        raise ReceiptError("panel.seats must contain both seats exactly once")
    return {(seed, seat) for seed in normalized_seeds for seat in normalized_seats}


def _validate_config(receipt: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    release = _latest_release(manifest)
    expected_live = _mapping(release.get("config"), "manifest latest release.config")
    submission = _mapping(release.get("submission_archive"), "manifest latest release.submission_archive")
    expected_submission_sha = _sha256(
        submission.get("sha256"), "manifest latest release.submission_archive.sha256"
    )

    baseline = _mapping(receipt.get("baseline"), "baseline")
    if baseline.get("submission_archive_sha256") != expected_submission_sha:
        raise ReceiptError("baseline.submission_archive_sha256 does not match the live-submission release")
    baseline_config = _mapping(baseline.get("config"), "baseline.config")
    for key, expected in expected_live.items():
        if key not in baseline_config:
            raise ReceiptError(f"baseline.config missing live-submission key: {key}")
        if baseline_config[key] != expected:
            raise ReceiptError(
                f"baseline.config[{key!r}]={baseline_config[key]!r} "
                f"does not match live submission {expected!r}"
            )

    candidate = _mapping(receipt.get("candidate"), "candidate")
    candidate_config = _mapping(candidate.get("config"), "candidate.config")
    overrides = _mapping(candidate.get("config_overrides"), "candidate.config_overrides")
    if set(candidate_config) != set(baseline_config):
        raise ReceiptError("candidate.config key set must exactly match baseline.config")
    expected_candidate = dict(baseline_config)
    unknown = sorted(set(overrides) - set(expected_candidate))
    if unknown:
        raise ReceiptError(f"candidate.config_overrides contains unknown keys: {unknown}")
    expected_candidate.update(overrides)
    if dict(candidate_config) != expected_candidate:
        raise ReceiptError("candidate.config differs from baseline by more than declared config_overrides")


def _validate_provenance(receipt: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    interpreter = _mapping(receipt.get("interpreter"), "interpreter")
    if interpreter.get("commit") != OFFICIAL_INTERPRETER_COMMIT:
        raise ReceiptError(f"interpreter.commit must be pinned official {OFFICIAL_INTERPRETER_COMMIT}")
    _sha256(interpreter.get("blob_sha256"), "interpreter.blob_sha256")
    if interpreter.get("verified_clean") is not True:
        raise ReceiptError("interpreter.verified_clean must be true")

    base = _mapping(manifest.get("base"), "manifest.base")
    expected_base_sha = _sha256(base.get("sha256"), "manifest.base.sha256")
    candidate = _mapping(receipt.get("candidate"), "candidate")
    if candidate.get("builder") != "build_v3.py":
        raise ReceiptError("candidate.builder must be build_v3.py")
    if candidate.get("built_from_pinned_archive") is not True:
        raise ReceiptError("candidate.built_from_pinned_archive must be true")
    if candidate.get("base_archive_sha256") != expected_base_sha:
        raise ReceiptError("candidate.base_archive_sha256 does not match manifest.base.sha256")
    _sha256(candidate.get("package_sha256"), "candidate.package_sha256")


def _validate_panel_and_results(
    receipt: Mapping[str, Any], panel: Mapping[str, Any]
) -> dict[str, float | int]:
    expected = _expected_cells(panel)
    gate = _mapping(receipt.get("panel"), "receipt.panel")
    if gate.get("seeds") != panel.get("seeds"):
        raise ReceiptError("receipt.panel.seeds must exactly match OFFICIAL-GATE-PANEL.json")
    if gate.get("seats") != panel.get("seats"):
        raise ReceiptError("receipt.panel.seats must exactly match OFFICIAL-GATE-PANEL.json")
    if gate.get("seed_list_sha256") != panel.get("seed_list_sha256"):
        raise ReceiptError("receipt.panel.seed_list_sha256 mismatch")
    if gate.get("games_per_opponent") != panel.get("games_per_opponent"):
        raise ReceiptError("receipt.panel.games_per_opponent mismatch")

    opponent = _mapping(receipt.get("opponent"), "opponent")
    if not isinstance(opponent.get("name"), str) or not opponent["name"].strip():
        raise ReceiptError("opponent.name must be a non-empty string")
    _sha256(opponent.get("sha256"), "opponent.sha256")
    if opponent.get("same_bytes_between_arms") is not True:
        raise ReceiptError("opponent.same_bytes_between_arms must be true")

    rows = _list(receipt.get("per_cell_results"), "per_cell_results")
    seen: set[tuple[int, int]] = set()
    deltas: list[float] = []
    for idx, row_any in enumerate(rows):
        row = _mapping(row_any, f"per_cell_results[{idx}]")
        seed = row.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ReceiptError(f"per_cell_results[{idx}].seed must be an integer")
        seat = _seat(row.get("candidate_seat"), f"per_cell_results[{idx}].candidate_seat")
        key = (seed, seat)
        if key not in expected:
            raise ReceiptError(f"per_cell_results[{idx}] is outside the frozen panel: {key}")
        if key in seen:
            raise ReceiptError(f"duplicate frozen panel cell: {key}")
        seen.add(key)
        baseline = _score_pair(row.get("baseline_scores"), f"per_cell_results[{idx}].baseline_scores")
        candidate = _score_pair(row.get("candidate_scores"), f"per_cell_results[{idx}].candidate_scores")
        b_own, b_rival = (baseline[0], baseline[1]) if seat == 0 else (baseline[1], baseline[0])
        c_own, c_rival = (candidate[0], candidate[1]) if seat == 0 else (candidate[1], candidate[0])
        delta = (c_own - c_rival) - (b_own - b_rival)
        supplied = _number(row.get("delta_m"), f"per_cell_results[{idx}].delta_m")
        if not math.isclose(supplied, delta, rel_tol=0.0, abs_tol=1e-9):
            raise ReceiptError(
                f"per_cell_results[{idx}].delta_m={supplied} "
                f"disagrees with seat-aware recomputation {delta}"
            )
        deltas.append(delta)

    missing = sorted(expected - seen)
    if missing:
        raise ReceiptError(f"partial frozen panel; missing cells: {missing[:5]}")
    if len(rows) != len(expected):
        raise ReceiptError(f"per_cell_results must contain exactly {len(expected)} frozen cells")

    aggregate = _mapping(receipt.get("aggregate"), "aggregate")
    mean = sum(deltas) / len(deltas)
    supplied_mean = _number(aggregate.get("mean_delta_m"), "aggregate.mean_delta_m")
    if not math.isclose(supplied_mean, mean, rel_tol=0.0, abs_tol=1e-9):
        raise ReceiptError(f"aggregate.mean_delta_m={supplied_mean} disagrees with recomputed {mean}")
    return {"cells": len(rows), "mean_delta_m": mean}


def validate_receipt(
    receipt: Mapping[str, Any],
    manifest: Mapping[str, Any],
    panel: Mapping[str, Any],
) -> dict[str, Any]:
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ReceiptError(f"schema must be {RECEIPT_SCHEMA}")

    mode = receipt.get("mode")
    if mode == "practice":
        if receipt.get("official_gate_pass") is not False:
            raise ReceiptError("practice receipts must set official_gate_pass=false")
        reason = receipt.get("practice_reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ReceiptError("practice receipts must state a non-empty practice_reason")
        return {
            "valid": True,
            "mode": "practice",
            "official_gate_eligible": False,
            "reason": reason.strip(),
        }
    if mode != "official":
        raise ReceiptError("mode must be exactly 'official' or 'practice'")

    _validate_provenance(receipt, manifest)
    _validate_config(receipt, manifest)
    result = _validate_panel_and_results(receipt, panel)
    return {
        "valid": True,
        "mode": "official",
        "official_gate_eligible": True,
        **result,
    }


def _read_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"cannot read {label} JSON {path}: {exc}") from exc
    return _mapping(value, label)


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--manifest", type=Path, default=here / "V3-MANIFEST.json")
    parser.add_argument("--panel", type=Path, default=here / "OFFICIAL-GATE-PANEL.json")
    args = parser.parse_args(argv)
    try:
        result = validate_receipt(
            _read_json(args.receipt, "receipt"),
            _read_json(args.manifest, "manifest"),
            _read_json(args.panel, "panel"),
        )
    except ReceiptError as exc:
        print(f"FIDELITY ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
