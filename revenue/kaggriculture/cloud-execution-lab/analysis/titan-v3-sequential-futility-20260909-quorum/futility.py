#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed partial-panel futility gate for Titan paired game matrices.

Exit 0 = complete panel delegated to canonical gate and PROMOTE.
Exit 2 = INVALID evidence.
Exit 3 = FUTILE partial panel or complete canonical REJECT.
Exit 4 = valid partial panel that must CONTINUE.

A partial panel can never promote.  Without a score envelope this tool only
uses combinatorial or already-irreversible proofs.  A score envelope enables
additional optimistic numeric bounds and is accepted only when it is bound to
both the exact promotion contract and an immutable certificate file.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import statistics
import sys
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Mapping, Sequence

HERE = Path(__file__).resolve().parent
DEFAULT_GATE_DIR = HERE.parent.parent / "titan-v3-paired-game-gate"
GATE_DIR = Path(os.environ.get("TITAN_PAIRED_GATE_DIR", DEFAULT_GATE_DIR)).resolve()
if not GATE_DIR.is_dir():
    raise RuntimeError(f"paired-game gate directory not found: {GATE_DIR}")
if str(GATE_DIR) not in sys.path:
    sys.path.insert(0, str(GATE_DIR))

from contract import validate_contract, validate_evidence  # noqa: E402
from gate_common import (  # noqa: E402
    CellKey,
    Game,
    GateError,
    MAX_JSON_BYTES,
    MAX_JSONL_BYTES,
    SCHEMA_VERSION,
    atomic_write_json,
    finite_number,
    is_int,
    read_json,
    regular_file,
    sha256_file,
    snapshot_regular_file,
    strict_loads,
)
import gate as paired_gate  # noqa: E402
from panel_load import expected_keys  # noqa: E402

MAX_CERTIFICATE_BYTES = 16 * 1024 * 1024
ENVELOPE_FIELDS = {
    "schema_version",
    "panel_id",
    "contract_sha256",
    "terminal_score_min",
    "terminal_score_max",
    "certificate_sha256",
}


def _hex64(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise GateError(f"{label}: expected 64 hexadecimal characters")
    try:
        int(value, 16)
    except ValueError as exc:
        raise GateError(f"{label}: expected hexadecimal characters") from exc
    return value.lower()


def _safe_sum(values: Iterable[float], *, label: str) -> float:
    try:
        value = math.fsum(values)
    except (OverflowError, ValueError) as exc:
        raise GateError(f"{label}: derived sum is not finite") from exc
    return finite_number(value, label=label)


def _safe_difference(left: float, right: float, *, label: str) -> float:
    try:
        value = left - right
    except (OverflowError, ValueError) as exc:
        raise GateError(f"{label}: derived difference is not finite") from exc
    return finite_number(value, label=label)


def _safe_mean(values: Sequence[float], *, label: str) -> float | None:
    if not values:
        return None
    return finite_number(_safe_sum(values, label=f"{label}.sum") / len(values), label=label)


def _safe_median(values: Sequence[float], *, label: str) -> float | None:
    if not values:
        return None
    try:
        value = statistics.median(values)
    except (OverflowError, ValueError) as exc:
        raise GateError(f"{label}: derived median is not finite") from exc
    return finite_number(value, label=label)


def _median_allow_infinity(values: Sequence[float]) -> float:
    if not values:
        return math.inf
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    left, right = ordered[middle - 1], ordered[middle]
    if math.isinf(left) or math.isinf(right):
        return math.inf if right > 0 else -math.inf
    return left / 2.0 + right / 2.0


def _json_bound(value: float) -> float | None:
    return None if not math.isfinite(value) else value


def _result(margin: float) -> str:
    return "W" if margin > 0 else ("T" if margin == 0 else "L")


def _rank(result: str) -> int:
    return {"L": 0, "T": 1, "W": 2}[result]


def load_partial_games(
    path: Path,
    *,
    label: str,
    expected: set[CellKey],
) -> dict[CellKey, Game]:
    """Load a valid exact subset of the declared panel.

    Missing rows mean not-yet-run.  An explicit timeout/error/non-complete row
    is evidence failure, not missingness, and invalidates the snapshot.
    """

    path = regular_file(path, max_bytes=MAX_JSONL_BYTES, label=label)
    rows: dict[CellKey, Game] = {}
    seen: set[CellKey] = set()
    failures: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            obj = strict_loads(raw, label=f"{label} line {line_number}")
            if not isinstance(obj, dict):
                raise GateError(f"{label} line {line_number}: row must be an object")
            opponent = obj.get("opponent")
            seed = obj.get("seed")
            seat = obj.get("candidate_seat")
            if not isinstance(opponent, str) or not opponent:
                raise GateError(f"{label} line {line_number}: invalid opponent")
            if not is_int(seed):
                raise GateError(f"{label} line {line_number}: invalid seed")
            if not is_int(seat) or seat not in (0, 1):
                raise GateError(
                    f"{label} line {line_number}: candidate_seat must be 0 or 1"
                )
            key = CellKey(opponent, seed, seat)
            if key in seen:
                raise GateError(
                    f"{label}: duplicate cell {key.as_list()} at line {line_number}"
                )
            seen.add(key)
            if key not in expected:
                raise GateError(
                    f"{label}: extra cell {key.as_list()} at line {line_number}"
                )
            if obj.get("status") != "complete":
                failures.append(
                    {
                        "key": key.as_list(),
                        "line": line_number,
                        "status": obj.get("status"),
                        "error": obj.get("error"),
                    }
                )
                continue
            scores = obj.get("scores")
            if not isinstance(scores, list) or len(scores) != 2:
                raise GateError(
                    f"{label} line {line_number}: scores must have exactly two entries"
                )
            rows[key] = Game(
                key,
                (
                    finite_number(
                        scores[0], label=f"{label} line {line_number} scores[0]"
                    ),
                    finite_number(
                        scores[1], label=f"{label} line {line_number} scores[1]"
                    ),
                ),
                line_number,
            )
    if failures:
        raise GateError(
            f"{label}: non-complete cells: {json.dumps(failures, sort_keys=True)}"
        )
    return rows


def validate_envelope(
    obj: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    certificate_sha256: str,
) -> dict[str, Any]:
    missing = sorted(ENVELOPE_FIELDS - set(obj))
    extra = sorted(set(obj) - ENVELOPE_FIELDS)
    if missing or extra:
        raise GateError(
            f"envelope keys mismatch; missing={missing}, extra={extra}"
        )
    if not is_int(obj["schema_version"]) or obj["schema_version"] != SCHEMA_VERSION:
        raise GateError(
            f"envelope.schema_version must equal integer {SCHEMA_VERSION}"
        )
    if obj["panel_id"] != contract["panel_id"]:
        raise GateError("envelope.panel_id does not match contract")
    declared_contract = _hex64(
        obj["contract_sha256"], label="envelope.contract_sha256"
    )
    if declared_contract != contract_sha256:
        raise GateError(
            "envelope.contract_sha256 does not match the exact contract snapshot"
        )
    declared_certificate = _hex64(
        obj["certificate_sha256"], label="envelope.certificate_sha256"
    )
    if declared_certificate != certificate_sha256:
        raise GateError(
            "envelope.certificate_sha256 does not match the exact certificate snapshot"
        )
    lower = finite_number(
        obj["terminal_score_min"], label="envelope.terminal_score_min"
    )
    upper = finite_number(
        obj["terminal_score_max"], label="envelope.terminal_score_max"
    )
    if lower > upper:
        raise GateError("envelope terminal_score_min exceeds terminal_score_max")
    span = _safe_difference(upper, lower, label="envelope terminal score span")
    _safe_sum((span, span), label="envelope doubled terminal score span")
    return {
        "terminal_score_min": lower,
        "terminal_score_max": upper,
        "terminal_score_span": span,
        "contract_sha256": declared_contract,
        "certificate_sha256": declared_certificate,
    }


def _validate_scores_in_envelope(
    rows: Mapping[CellKey, Game],
    *,
    label: str,
    envelope: Mapping[str, Any],
) -> None:
    lower = envelope["terminal_score_min"]
    upper = envelope["terminal_score_max"]
    for key, game in rows.items():
        for index, score in enumerate(game.scores):
            if score < lower or score > upper:
                raise GateError(
                    f"{label} cell {key.as_list()} scores[{index}]={score} "
                    f"outside certified envelope [{lower}, {upper}]"
                )


def _observed_metrics(
    baseline: Mapping[CellKey, Game],
    candidate: Mapping[CellKey, Game],
) -> tuple[dict[CellKey, dict[str, Any]], dict[str, int]]:
    cells: dict[CellKey, dict[str, Any]] = {}
    counts = {
        "result_regressions": 0,
        "baseline_win_regressions": 0,
        "new_losses": 0,
        "changed_cells": 0,
    }
    for key in sorted(candidate):
        base = baseline[key]
        cand = candidate[key]
        baseline_margin = _safe_difference(
            base.own, base.rival, label=f"cell {key.as_list()} baseline margin"
        )
        candidate_margin = _safe_difference(
            cand.own, cand.rival, label=f"cell {key.as_list()} candidate margin"
        )
        own_delta = _safe_difference(
            cand.own, base.own, label=f"cell {key.as_list()} own delta"
        )
        margin_delta = _safe_difference(
            candidate_margin,
            baseline_margin,
            label=f"cell {key.as_list()} margin delta",
        )
        baseline_result = _result(baseline_margin)
        candidate_result = _result(candidate_margin)
        regression = _rank(candidate_result) < _rank(baseline_result)
        if regression:
            counts["result_regressions"] += 1
            counts["baseline_win_regressions"] += baseline_result == "W"
            counts["new_losses"] += (
                candidate_result == "L" and baseline_result != "L"
            )
        changed = base.scores != cand.scores
        counts["changed_cells"] += changed
        cells[key] = {
            "own_delta": own_delta,
            "margin_delta": margin_delta,
            "baseline_result": baseline_result,
            "candidate_result": candidate_result,
            "changed": changed,
        }
    return cells, counts


def _missing_own_upper(
    key: CellKey,
    *,
    baseline: Mapping[CellKey, Game],
    envelope: Mapping[str, Any] | None,
) -> float:
    if envelope is None:
        return math.inf
    upper = envelope["terminal_score_max"]
    if key in baseline:
        return _safe_difference(
            upper,
            baseline[key].own,
            label=f"cell {key.as_list()} optimistic own delta",
        )
    return envelope["terminal_score_span"]


def _missing_margin_upper(
    key: CellKey,
    *,
    baseline: Mapping[CellKey, Game],
    envelope: Mapping[str, Any] | None,
) -> float:
    if envelope is None:
        return math.inf
    span = envelope["terminal_score_span"]
    if key in baseline:
        base_margin = _safe_difference(
            baseline[key].own,
            baseline[key].rival,
            label=f"cell {key.as_list()} baseline margin for optimistic bound",
        )
        return _safe_difference(
            span,
            base_margin,
            label=f"cell {key.as_list()} optimistic margin delta",
        )
    return _safe_sum(
        (span, span), label=f"cell {key.as_list()} generic optimistic margin delta"
    )


def _lower_requirement(
    name: str,
    *,
    threshold: float,
    observed: float | None,
    optimistic: float,
    proof: str,
) -> dict[str, Any]:
    impossible = math.isfinite(optimistic) and optimistic < threshold
    return {
        "name": name,
        "op": ">=",
        "threshold": threshold,
        "observed": observed,
        "optimistic_final": _json_bound(optimistic),
        "optimistic_final_unbounded": not math.isfinite(optimistic),
        "futility_proven": impossible,
        "can_still_pass": not impossible,
        "proof": proof,
    }


def _upper_requirement(
    name: str,
    *,
    threshold: int,
    observed_lower_bound: int,
    proof: str,
    forced_keys: Sequence[Any] | None = None,
) -> dict[str, Any]:
    impossible = observed_lower_bound > threshold
    result: dict[str, Any] = {
        "name": name,
        "op": "<=",
        "threshold": threshold,
        "minimum_final": observed_lower_bound,
        "futility_proven": impossible,
        "can_still_pass": not impossible,
        "proof": proof,
    }
    if forced_keys is not None:
        result["forced_keys"] = list(forced_keys)
    return result


def analyze_futility(
    *,
    contract: Mapping[str, Any],
    baseline: Mapping[CellKey, Game],
    candidate: Mapping[CellKey, Game],
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    expected = expected_keys(contract)
    observed, counts = _observed_metrics(baseline, candidate)
    missing = sorted(expected - set(candidate))
    total_cells = len(expected)
    policy = contract["policy"]
    own_values = [observed[key]["own_delta"] for key in sorted(observed)]
    margin_values = [observed[key]["margin_delta"] for key in sorted(observed)]
    own_missing_upper = {
        key: _missing_own_upper(key, baseline=baseline, envelope=envelope)
        for key in missing
    }
    margin_missing_upper = {
        key: _missing_margin_upper(key, baseline=baseline, envelope=envelope)
        for key in missing
    }

    checks: list[dict[str, Any]] = []

    observed_own_mean = _safe_mean(own_values, label="observed own delta mean")
    if any(math.isinf(value) for value in own_missing_upper.values()):
        optimistic_own_mean = math.inf
        own_mean_proof = (
            "partial means are intentionally unbounded without a contract-bound "
            "terminal-score envelope"
        )
    else:
        optimistic_own_mean = finite_number(
            _safe_sum(
                [*own_values, *own_missing_upper.values()],
                label="optimistic final own delta sum",
            )
            / total_cells,
            label="optimistic final own delta mean",
        )
        own_mean_proof = (
            "every missing candidate-own score was replaced by its certified "
            "cell-specific maximum"
        )
    checks.append(
        _lower_requirement(
            "mean_own_delta",
            threshold=policy["min_mean_own_delta"],
            observed=observed_own_mean,
            optimistic=optimistic_own_mean,
            proof=own_mean_proof,
        )
    )

    median_inputs = [*own_values, *own_missing_upper.values()]
    optimistic_median = _median_allow_infinity(median_inputs)
    checks.append(
        _lower_requirement(
            "median_own_delta",
            threshold=policy["min_median_own_delta"],
            observed=_safe_median(own_values, label="observed own delta median"),
            optimistic=optimistic_median,
            proof=(
                "missing cells are assigned their certified upper deltas; "
                "without an envelope they are +infinity, so only an already-fixed "
                "middle order statistic can prove futility"
            ),
        )
    )

    observed_margin_mean = _safe_mean(
        margin_values, label="observed margin delta mean"
    )
    if any(math.isinf(value) for value in margin_missing_upper.values()):
        optimistic_margin_mean = math.inf
        margin_mean_proof = (
            "partial margin means are intentionally unbounded without a "
            "contract-bound terminal-score envelope"
        )
    else:
        optimistic_margin_mean = finite_number(
            _safe_sum(
                [*margin_values, *margin_missing_upper.values()],
                label="optimistic final margin delta sum",
            )
            / total_cells,
            label="optimistic final margin delta mean",
        )
        margin_mean_proof = (
            "every missing candidate margin was replaced by its certified maximum"
        )
    checks.append(
        _lower_requirement(
            "mean_margin_delta",
            threshold=policy["min_mean_margin_delta"],
            observed=observed_margin_mean,
            optimistic=optimistic_margin_mean,
            proof=margin_mean_proof,
        )
    )

    observed_positive_cells = sum(value > 0 for value in own_values)
    possible_positive_missing = sum(
        upper > 0 for upper in own_missing_upper.values()
    )
    optimistic_positive_cells = observed_positive_cells + possible_positive_missing
    checks.append(
        _lower_requirement(
            "positive_cell_fraction",
            threshold=policy["min_positive_cell_fraction"],
            observed=(
                observed_positive_cells / len(own_values) if own_values else None
            ),
            optimistic=optimistic_positive_cells / total_cells,
            proof=(
                "every missing cell that can still have positive own-cash delta "
                "is counted as positive"
            ),
        )
    )

    pair_records = []
    optimistic_positive_pairs = 0
    completed_positive_pairs = 0
    for opponent in contract["opponents"]:
        for seed in contract["seeds"]:
            pair_keys = [CellKey(opponent, seed, seat) for seat in contract["seats"]]
            upper_values: list[float] = []
            complete = True
            exact_values: list[float] = []
            for key in pair_keys:
                if key in observed:
                    value = observed[key]["own_delta"]
                    upper_values.append(value)
                    exact_values.append(value)
                else:
                    complete = False
                    upper_values.append(own_missing_upper[key])
            if any(math.isinf(value) for value in upper_values):
                upper_mean = math.inf
            else:
                upper_mean = finite_number(
                    _safe_sum(
                        upper_values,
                        label=f"pair {[opponent, seed]} optimistic own delta sum",
                    )
                    / 2,
                    label=f"pair {[opponent, seed]} optimistic own delta mean",
                )
            can_be_positive = upper_mean > 0
            optimistic_positive_pairs += can_be_positive
            actual_mean = None
            if complete:
                actual_mean = finite_number(
                    _safe_sum(
                        exact_values,
                        label=f"pair {[opponent, seed]} observed own delta sum",
                    )
                    / 2,
                    label=f"pair {[opponent, seed]} observed own delta mean",
                )
                completed_positive_pairs += actual_mean > 0
            pair_records.append(
                {
                    "opponent": opponent,
                    "seed": seed,
                    "complete": complete,
                    "observed_mean": actual_mean,
                    "optimistic_mean": _json_bound(upper_mean),
                    "optimistic_mean_unbounded": not math.isfinite(upper_mean),
                    "can_be_positive": can_be_positive,
                }
            )
    total_pairs = len(contract["opponents"]) * len(contract["seeds"])
    checks.append(
        _lower_requirement(
            "positive_pair_fraction",
            threshold=policy["min_positive_pair_fraction"],
            observed=(
                completed_positive_pairs
                / sum(record["complete"] for record in pair_records)
                if any(record["complete"] for record in pair_records)
                else None
            ),
            optimistic=optimistic_positive_pairs / total_pairs,
            proof=(
                "each incomplete seat-pair is positive only when the sum of exact "
                "observations and all missing-cell upper bounds can exceed zero"
            ),
        )
    )

    for name in (
        "result_regressions",
        "baseline_win_regressions",
        "new_losses",
    ):
        checks.append(
            _upper_requirement(
                name,
                threshold=policy[f"max_{name}"],
                observed_lower_bound=counts[name],
                proof="an observed result regression cannot be undone by later cells",
            )
        )

    def forced_negative_strata(
        groups: Mapping[Any, Sequence[CellKey]], *, label: str
    ) -> tuple[list[Any], list[dict[str, Any]]]:
        forced: list[Any] = []
        records: list[dict[str, Any]] = []
        for group, keys in groups.items():
            values: list[float] = []
            for key in keys:
                if key in observed:
                    values.append(observed[key]["own_delta"])
                else:
                    values.append(own_missing_upper[key])
            if any(math.isinf(value) for value in values):
                upper_mean = math.inf
            else:
                upper_mean = finite_number(
                    _safe_sum(values, label=f"{label} {group!r} optimistic sum")
                    / len(keys),
                    label=f"{label} {group!r} optimistic mean",
                )
            is_forced = upper_mean < 0
            if is_forced:
                forced.append(group)
            records.append(
                {
                    "group": group,
                    "optimistic_mean": _json_bound(upper_mean),
                    "optimistic_mean_unbounded": not math.isfinite(upper_mean),
                    "forced_negative": is_forced,
                    "observed_cells": sum(key in observed for key in keys),
                    "total_cells": len(keys),
                }
            )
        return forced, records

    opponent_groups = {
        opponent: [
            CellKey(opponent, seed, seat)
            for seed in contract["seeds"]
            for seat in contract["seats"]
        ]
        for opponent in contract["opponents"]
    }
    seat_groups = {
        seat: [
            CellKey(opponent, seed, seat)
            for opponent in contract["opponents"]
            for seed in contract["seeds"]
        ]
        for seat in contract["seats"]
    }
    forced_opponents, opponent_records = forced_negative_strata(
        opponent_groups, label="opponent"
    )
    forced_seats, seat_records = forced_negative_strata(
        seat_groups, label="seat"
    )
    checks.append(
        _upper_requirement(
            "negative_opponent_strata",
            threshold=policy["max_negative_opponent_strata"],
            observed_lower_bound=len(forced_opponents),
            proof=(
                "a stratum is counted only when even every missing cell at its "
                "optimistic upper delta leaves the final mean negative"
            ),
            forced_keys=forced_opponents,
        )
    )
    checks.append(
        _upper_requirement(
            "negative_seat_strata",
            threshold=policy["max_negative_seat_strata"],
            observed_lower_bound=len(forced_seats),
            proof=(
                "a seat is counted only when even every missing cell at its "
                "optimistic upper delta leaves the final mean negative"
            ),
            forced_keys=forced_seats,
        )
    )

    if policy["min_worst_cell_own_delta"] is None:
        checks.append(
            {
                "name": "worst_cell_own_delta",
                "enabled": False,
                "futility_proven": False,
                "can_still_pass": True,
                "proof": "disabled by the frozen promotion contract",
            }
        )
    else:
        optimistic_worst_values = [*own_values, *own_missing_upper.values()]
        optimistic_worst = (
            min(optimistic_worst_values)
            if optimistic_worst_values
            else math.inf
        )
        checks.append(
            _lower_requirement(
                "worst_cell_own_delta",
                threshold=policy["min_worst_cell_own_delta"],
                observed=min(own_values) if own_values else None,
                optimistic=optimistic_worst,
                proof=(
                    "the final worst cell cannot exceed the worst exact observed "
                    "delta or any missing cell's certified maximum"
                ),
            )
        )

    possible_changed_cells = counts["changed_cells"] + len(missing)
    any_change_impossible = (
        policy["require_any_change"] and possible_changed_cells == 0
    )
    checks.append(
        {
            "name": "any_score_change",
            "op": "> 0" if policy["require_any_change"] else ">= 0",
            "threshold": 0,
            "observed": counts["changed_cells"],
            "optimistic_final": possible_changed_cells,
            "futility_proven": any_change_impossible,
            "can_still_pass": not any_change_impossible,
            "proof": (
                "each missing cell is optimistically allowed to change; identity "
                "is futile only after the complete grid"
            ),
        }
    )

    futile = [check["name"] for check in checks if check["futility_proven"]]
    return {
        "coverage": {
            "expected_cells": total_cells,
            "baseline_cells": len(baseline),
            "candidate_cells": len(candidate),
            "matched_cells": len(observed),
            "remaining_candidate_cells": len(missing),
            "complete_pairs": sum(record["complete"] for record in pair_records),
            "total_pairs": total_pairs,
        },
        "observed": {
            "own_delta_mean": observed_own_mean,
            "own_delta_median": _safe_median(own_values, label="observed own delta median"),
            "margin_delta_mean": observed_margin_mean,
            **counts,
        },
        "checks": checks,
        "futility_reasons": futile,
        "pair_bounds": pair_records,
        "opponent_bounds": opponent_records,
        "seat_bounds": seat_records,
    }


def _verify_snapshots(snapshots: Mapping[str, Any]) -> None:
    changed: dict[str, dict[str, str]] = {}
    for name, snapshot in snapshots.items():
        observed = sha256_file(snapshot.path)
        if observed != snapshot.sha256:
            changed[name] = {"expected": snapshot.sha256, "observed": observed}
    if changed:
        raise GateError(f"private input snapshot changed during evaluation: {changed}")


def run_futility(
    *,
    contract_path: Path,
    evidence_path: Path,
    baseline_path: Path,
    candidate_path: Path,
    envelope_path: Path | None = None,
    certificate_path: Path | None = None,
) -> tuple[dict[str, Any], int]:
    if (envelope_path is None) != (certificate_path is None):
        raise GateError(
            "--envelope and --bound-certificate must be supplied together"
        )
    sources: dict[str, tuple[Path, int, str]] = {
        "contract": (contract_path, MAX_JSON_BYTES, "contract"),
        "evidence": (evidence_path, MAX_JSON_BYTES, "evidence"),
        "baseline_games": (baseline_path, MAX_JSONL_BYTES, "baseline games"),
        "candidate_games": (candidate_path, MAX_JSONL_BYTES, "candidate games"),
    }
    if envelope_path is not None and certificate_path is not None:
        sources["envelope"] = (envelope_path, MAX_JSON_BYTES, "score envelope")
        sources["bound_certificate"] = (
            certificate_path,
            MAX_CERTIFICATE_BYTES,
            "score-bound certificate",
        )

    with TemporaryDirectory(prefix="titan-v3-sequential-futility-") as directory:
        snapshot_root = Path(directory)
        snapshots = {
            name: snapshot_regular_file(
                path,
                directory=snapshot_root,
                max_bytes=max_bytes,
                label=label,
            )
            for name, (path, max_bytes, label) in sources.items()
        }
        paths = {name: snapshot.path for name, snapshot in snapshots.items()}
        hashes = {name: snapshot.sha256 for name, snapshot in snapshots.items()}
        sizes = {name: snapshot.bytes for name, snapshot in snapshots.items()}

        contract = validate_contract(read_json(paths["contract"], label="contract"))
        evidence = validate_evidence(
            read_json(paths["evidence"], label="evidence"), contract
        )
        expected = expected_keys(contract)
        baseline = load_partial_games(
            paths["baseline_games"], label="baseline games", expected=expected
        )
        candidate = load_partial_games(
            paths["candidate_games"], label="candidate games", expected=expected
        )
        missing_baseline = sorted(set(candidate) - set(baseline))
        if missing_baseline:
            raise GateError(
                "candidate cells missing matching baseline rows: "
                f"{[key.as_list() for key in missing_baseline]}"
            )

        envelope = None
        if envelope_path is not None:
            envelope = validate_envelope(
                read_json(paths["envelope"], label="score envelope"),
                contract=contract,
                contract_sha256=hashes["contract"],
                certificate_sha256=hashes["bound_certificate"],
            )
            _validate_scores_in_envelope(
                baseline, label="baseline games", envelope=envelope
            )
            _validate_scores_in_envelope(
                candidate, label="candidate games", envelope=envelope
            )

        analysis = analyze_futility(
            contract=contract,
            baseline=baseline,
            candidate=candidate,
            envelope=envelope,
        )
        complete = set(candidate) == expected and set(baseline) == expected
        common = {
            "schema_version": SCHEMA_VERSION,
            "valid": True,
            "panel_id": contract["panel_id"],
            "baseline_name": contract["baseline_name"],
            "candidate_name": contract["candidate_name"],
            "input_sha256": hashes,
            "input_bytes": sizes,
            "input_binding": (
                "single-open private snapshots; hashes cover exactly parsed bytes"
            ),
            "provenance": evidence["provenance"],
            "exact_command": evidence["exact_command"],
            "score_envelope": envelope,
            "analysis": analysis,
        }

        if complete:
            delegated, code = paired_gate.run_gate(
                contract_path=paths["contract"],
                evidence_path=paths["evidence"],
                baseline_path=paths["baseline_games"],
                candidate_path=paths["candidate_games"],
            )
            report = {
                **common,
                "mode": "complete-delegation",
                "partial_panel_can_promote": False,
                "verdict": delegated["verdict"],
                "delegated_gate": delegated,
            }
            _verify_snapshots(snapshots)
            return report, code

        futile = bool(analysis["futility_reasons"])
        report = {
            **common,
            "mode": "partial-futility-only",
            "partial_panel_can_promote": False,
            "verdict": "FUTILE" if futile else "CONTINUE",
            "next_action": (
                "cancel remaining candidate cells"
                if futile
                else "continue the immutable declared panel"
            ),
        }
        _verify_snapshots(snapshots)
        return report, 3 if futile else 4


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("contract", "evidence", "baseline", "candidate", "report"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--envelope", type=Path)
    parser.add_argument("--bound-certificate", type=Path)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    try:
        report, code = run_futility(
            contract_path=args.contract,
            evidence_path=args.evidence,
            baseline_path=args.baseline,
            candidate_path=args.candidate,
            envelope_path=args.envelope,
            certificate_path=args.bound_certificate,
        )
    except (GateError, OSError, UnicodeError) as exc:
        report, code = {
            "schema_version": SCHEMA_VERSION,
            "verdict": "INVALID",
            "valid": False,
            "error": str(exc),
        }, 2
    atomic_write_json(args.report, report)
    if not args.quiet:
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
