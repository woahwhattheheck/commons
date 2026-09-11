#!/usr/bin/env python3
"""Summarize paired TITAN evaluator cells without trusting headline averages.

Generic ``scores`` arrays are evaluator/seat ordered: ``[seat0, seat1]``.
Explicit ``own``/``rival`` fields remain actor ordered. Each logical cell is
keyed by opponent, seed, and the candidate/our seat. Competitive margin is
always recomputed as (candidate_own - candidate_rival) -
(baseline_own - baseline_rival). A supplied delta_m is diagnostic only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Iterable, Mapping, Sequence


class DataError(ValueError):
    """Raised when evaluator evidence is incomplete, ambiguous, or malformed."""


_MISSING = object()
_EPS = 1e-9
_OPPONENT_KEYS = ("opponent", "opponent_name", "rival_name")
_SEED_KEYS = ("seed", "game_seed")
_SEAT_KEYS = ("candidate_seat", "seat", "our_seat")


def _first(mapping: Mapping[str, Any], keys: Iterable[str], default: Any = _MISSING) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    if default is _MISSING:
        raise DataError("missing required field; expected one of: " + ", ".join(keys))
    return default


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DataError(f"{label} must be a JSON number")
    out = float(value)
    if not math.isfinite(out):
        raise DataError(f"{label} must be finite")
    return out


def _seat(value: Any) -> int:
    if isinstance(value, str) and value in {"0", "1"}:
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
        raise DataError("seat must be 0 or 1")
    return value


def _resolved_opponent(mapping: Mapping[str, Any], label: str = "record") -> str:
    present: list[tuple[str, str]] = []
    for key in _OPPONENT_KEYS:
        if key not in mapping:
            continue
        value = mapping[key]
        if not isinstance(value, str) or not value.strip():
            raise DataError(f"{label}.{key} must be a non-empty string")
        present.append((key, value.strip()))
    if not present:
        raise DataError(f"{label} missing opponent; expected one of: " + ", ".join(_OPPONENT_KEYS))
    values = {value for _, value in present}
    if len(values) != 1:
        rendered = ", ".join(f"{key}={value!r}" for key, value in present)
        raise DataError(f"{label} has contradictory opponent aliases: {rendered}")
    return present[0][1]


def _seed(value: Any, label: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise DataError(f"{label} must be an integer or string")
    return str(value)


def _resolved_seed(mapping: Mapping[str, Any], label: str = "record") -> str:
    present = [(key, _seed(mapping[key], f"{label}.{key}")) for key in _SEED_KEYS if key in mapping]
    if not present:
        raise DataError(f"{label} missing seed; expected one of: " + ", ".join(_SEED_KEYS))
    values = {value for _, value in present}
    if len(values) != 1:
        rendered = ", ".join(f"{key}={value!r}" for key, value in present)
        raise DataError(f"{label} has contradictory seed aliases: {rendered}")
    return present[0][1]


def _resolved_seat(mapping: Mapping[str, Any], label: str = "record") -> int:
    present = [(key, _seat(mapping[key])) for key in _SEAT_KEYS if key in mapping]
    if not present:
        raise DataError(f"{label} missing seat; expected one of: " + ", ".join(_SEAT_KEYS))
    values = {value for _, value in present}
    if len(values) != 1:
        rendered = ", ".join(f"{key}={value}" for key, value in present)
        raise DataError(f"{label} has contradictory seat aliases: {rendered}")
    return present[0][1]


def _cell_key(record: Mapping[str, Any]) -> tuple[str, str, int]:
    return _resolved_opponent(record), _resolved_seed(record), _resolved_seat(record)


def _score_sequence(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise DataError(f"{label} must contain [seat0, seat1]")
    return value


def _seat_ordered_scores(scores: Any, seat: int, label: str) -> tuple[float, float]:
    row = _score_sequence(scores, label)
    seat0 = _number(row[0], f"{label}[0]")
    seat1 = _number(row[1], f"{label}[1]")
    return (seat0, seat1) if seat == 0 else (seat1, seat0)


def _resolved_numeric_alias(mapping: Mapping[str, Any], keys: Sequence[str], label: str) -> float | object:
    present = [(key, _number(mapping[key], f"{label}.{key}")) for key in keys if key in mapping]
    if not present:
        return _MISSING
    first = present[0][1]
    if any(not math.isclose(value, first, rel_tol=0.0, abs_tol=_EPS) for _, value in present[1:]):
        rendered = ", ".join(f"{key}={value:.12g}" for key, value in present)
        raise DataError(f"{label} has contradictory numeric aliases: {rendered}")
    return first


def _pairs_agree(left: tuple[float, float], right: tuple[float, float]) -> bool:
    return all(math.isclose(a, b, rel_tol=0.0, abs_tol=_EPS) for a, b in zip(left, right))


def _resolved_score_representations(label: str, representations: Sequence[tuple[str, tuple[float, float]]]) -> tuple[float, float]:
    if not representations:
        raise DataError(f"{label} missing score representation")
    first_name, first_pair = representations[0]
    for name, pair in representations[1:]:
        if not _pairs_agree(first_pair, pair):
            raise DataError(
                f"{label} has contradictory score representations: "
                f"{first_name}={first_pair!r}, {name}={pair!r}"
            )
    return first_pair


def _explicit_pair(mapping: Mapping[str, Any], own_keys: Sequence[str], rival_keys: Sequence[str], label: str) -> tuple[float, float] | object:
    own = _resolved_numeric_alias(mapping, own_keys, label)
    rival = _resolved_numeric_alias(mapping, rival_keys, label)
    if own is _MISSING and rival is _MISSING:
        return _MISSING
    if own is _MISSING or rival is _MISSING:
        raise DataError(f"{label} explicit own/rival representation is incomplete")
    return float(own), float(rival)


def _pair_from_mapping(mapping: Mapping[str, Any], label: str, seat: int) -> tuple[float, float]:
    representations: list[tuple[str, tuple[float, float]]] = []
    scores = mapping.get("scores", _MISSING)
    if scores is not _MISSING:
        representations.append(("scores", _seat_ordered_scores(scores, seat, f"{label}.scores")))
    explicit = _explicit_pair(
        mapping,
        ("own", "ours", "own_score", "our_score", "score"),
        ("rival", "rival_score", "opponent_score", "their_score"),
        label,
    )
    if explicit is not _MISSING:
        representations.append(("own/rival", explicit))
    return _resolved_score_representations(label, representations)


def _arm_scores(record: Mapping[str, Any], arm: str, seat: int) -> tuple[float, float]:
    representations: list[tuple[str, tuple[float, float]]] = []
    if arm in record:
        nested = record[arm]
        if not isinstance(nested, Mapping):
            raise DataError(f"{arm} must be an object")
        representations.append((arm, _pair_from_mapping(nested, arm, seat)))
    scores = record.get(f"{arm}_scores", _MISSING)
    if scores is not _MISSING:
        representations.append((f"{arm}_scores", _seat_ordered_scores(scores, seat, f"{arm}_scores")))
    explicit = _explicit_pair(
        record,
        (f"{arm}_own", f"{arm}_ours", f"{arm}_own_score", f"{arm}_our_score", f"{arm}_score"),
        (f"{arm}_rival", f"{arm}_rival_score", f"{arm}_opponent_score", f"{arm}_their_score"),
        arm,
    )
    if explicit is not _MISSING:
        representations.append((f"{arm}_own/rival", explicit))
    return _resolved_score_representations(arm, representations)


def _activation_mapping(record: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = record.get("activations")
    if direct is not None:
        if not isinstance(direct, Mapping):
            raise DataError("activations must be an object")
        return direct
    diagnostics = record.get("diagnostics")
    if diagnostics is None:
        return {}
    if not isinstance(diagnostics, Mapping):
        raise DataError("diagnostics must be an object")
    activations = diagnostics.get("activations", {})
    if not isinstance(activations, Mapping):
        raise DataError("diagnostics.activations must be an object")
    return activations


def _activation_state(value: Any, label: str) -> bool:
    if isinstance(value, bool):
        return value
    number = _number(value, label)
    if number < 0:
        raise DataError(f"{label} must not be negative")
    return number > 0


def _records_container(document: Any) -> list[Mapping[str, Any]]:
    if isinstance(document, list):
        rows = document
    elif isinstance(document, Mapping):
        rows = _MISSING
        for key in ("cells", "results", "games", "matches"):
            if key in document:
                rows = document[key]
                break
        if rows is _MISSING:
            raise DataError("input object must contain cells/results/games/matches or baseline+candidate arms")
    else:
        raise DataError("input must be a JSON list or object")
    if not isinstance(rows, list) or not rows:
        raise DataError("evidence cell list must be non-empty")
    if not all(isinstance(row, Mapping) for row in rows):
        raise DataError("every evidence cell must be an object")
    return list(rows)


def _pair_separate_arms(document: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    if "baseline" not in document or "candidate" not in document:
        return None
    if not isinstance(document["baseline"], list) or not isinstance(document["candidate"], list):
        return None
    indexed: dict[str, dict[tuple[str, str, int], Mapping[str, Any]]] = {}
    for arm in ("baseline", "candidate"):
        table: dict[tuple[str, str, int], Mapping[str, Any]] = {}
        for row in document[arm]:
            if not isinstance(row, Mapping):
                raise DataError(f"{arm} arm rows must be objects")
            key = _cell_key(row)
            if key in table:
                raise DataError(f"duplicate {arm} cell: {key}")
            table[key] = row
        if not table:
            raise DataError(f"{arm} arm must be non-empty")
        indexed[arm] = table
    baseline_keys = set(indexed["baseline"])
    candidate_keys = set(indexed["candidate"])
    if baseline_keys != candidate_keys:
        raise DataError(
            "arm cell sets differ; "
            f"missing_candidate={sorted(baseline_keys - candidate_keys)[:5]} "
            f"missing_baseline={sorted(candidate_keys - baseline_keys)[:5]}"
        )
    paired: list[dict[str, Any]] = []
    for key in sorted(baseline_keys):
        base = indexed["baseline"][key]
        cand = indexed["candidate"][key]
        bo, br = _pair_from_mapping(base, "baseline", key[2])
        co, cr = _pair_from_mapping(cand, "candidate", key[2])
        synthesized: dict[str, Any] = {
            "opponent": key[0], "seed": key[1], "seat": key[2],
            "baseline": {"own": bo, "rival": br},
            "candidate": {"own": co, "rival": cr},
        }
        activations = _activation_mapping(cand)
        if activations:
            synthesized["activations"] = dict(activations)
        for delta_key in ("delta_m", "deltaM", "delta_margin"):
            if delta_key in cand:
                synthesized[delta_key] = cand[delta_key]
                break
        paired.append(synthesized)
    return paired


def load_records(document: Any) -> list[Mapping[str, Any]]:
    if isinstance(document, Mapping):
        paired = _pair_separate_arms(document)
        if paired is not None:
            return paired
    return _records_container(document)


def _outcome(own: float, rival: float) -> str:
    if own > rival:
        return "W"
    if own < rival:
        return "L"
    return "T"


def _basic_stats(cells: Sequence[dict[str, Any]]) -> dict[str, Any]:
    deltas = [cell["delta_m"] for cell in cells]
    return {
        "count": len(cells),
        "mean_delta_m": statistics.fmean(deltas),
        "median_delta_m": statistics.median(deltas),
        "positive": sum(delta > _EPS for delta in deltas),
        "negative": sum(delta < -_EPS for delta in deltas),
        "zero": sum(abs(delta) <= _EPS for delta in deltas),
        "baseline_wtl": dict(sorted(Counter(c["baseline_outcome"] for c in cells).items())),
        "candidate_wtl": dict(sorted(Counter(c["candidate_outcome"] for c in cells).items())),
    }


def _public_cell(cell: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "opponent": cell["opponent"], "seed": cell["seed"], "seat": cell["seat"],
        "delta_m": cell["delta_m"], "baseline_margin": cell["baseline_margin"],
        "candidate_margin": cell["candidate_margin"],
        "baseline_outcome": cell["baseline_outcome"], "candidate_outcome": cell["candidate_outcome"],
    }


def analyze(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not records:
        raise DataError("evidence cell list must be non-empty")
    seen: set[tuple[str, str, int]] = set()
    cells: list[dict[str, Any]] = []
    supplied_mismatches: list[dict[str, Any]] = []
    feature_names: set[str] = set()
    for record in records:
        key = _cell_key(record)
        if key in seen:
            raise DataError(f"duplicate logical cell: {key}")
        seen.add(key)
        baseline_own, baseline_rival = _arm_scores(record, "baseline", key[2])
        candidate_own, candidate_rival = _arm_scores(record, "candidate", key[2])
        baseline_margin = baseline_own - baseline_rival
        candidate_margin = candidate_own - candidate_rival
        delta_m = candidate_margin - baseline_margin
        activations: dict[str, bool] = {}
        for name, raw in _activation_mapping(record).items():
            if not isinstance(name, str) or not name:
                raise DataError("activation names must be non-empty strings")
            activations[name] = _activation_state(raw, f"activations.{name}")
            feature_names.add(name)
        cell = {
            "opponent": key[0], "seed": key[1], "seat": key[2],
            "baseline_margin": baseline_margin, "candidate_margin": candidate_margin,
            "delta_m": delta_m,
            "baseline_outcome": _outcome(baseline_own, baseline_rival),
            "candidate_outcome": _outcome(candidate_own, candidate_rival),
            "activations": activations,
        }
        cells.append(cell)
        supplied = _MISSING
        supplied_key = None
        for name in ("delta_m", "deltaM", "delta_margin"):
            if name in record:
                supplied_key = name
                supplied = _number(record[name], name)
                break
        if supplied is not _MISSING and not math.isclose(supplied, delta_m, rel_tol=0.0, abs_tol=_EPS):
            supplied_mismatches.append({
                "opponent": key[0], "seed": key[1], "seat": key[2], "field": supplied_key,
                "supplied": supplied, "recomputed": delta_m,
            })
    ordered = sorted(cells, key=lambda c: (c["opponent"], c["seed"], c["seat"]))
    deltas = [cell["delta_m"] for cell in ordered]
    worst = min(ordered, key=lambda cell: cell["delta_m"])
    best = max(ordered, key=lambda cell: cell["delta_m"])
    transitions = Counter(f'{cell["baseline_outcome"]}->{cell["candidate_outcome"]}' for cell in ordered)
    new_losses = [_public_cell(cell) for cell in ordered if cell["baseline_outcome"] != "L" and cell["candidate_outcome"] == "L"]
    lost_wins = [_public_cell(cell) for cell in ordered if cell["baseline_outcome"] == "W" and cell["candidate_outcome"] != "W"]
    by_seat = {
        str(seat): _basic_stats([cell for cell in ordered if cell["seat"] == seat])
        for seat in (0, 1) if any(cell["seat"] == seat for cell in ordered)
    }
    by_opponent = {
        opponent: _basic_stats([cell for cell in ordered if cell["opponent"] == opponent])
        for opponent in sorted({cell["opponent"] for cell in ordered})
    }
    activation_summary: dict[str, Any] = {}
    for feature in sorted(feature_names):
        active = [cell for cell in ordered if cell["activations"].get(feature) is True]
        inactive = [cell for cell in ordered if cell["activations"].get(feature) is False]
        unknown = [cell for cell in ordered if feature not in cell["activations"]]
        activation_summary[feature] = {
            "active": _basic_stats(active) if active else {"count": 0},
            "inactive": _basic_stats(inactive) if inactive else {"count": 0},
            "unknown_count": len(unknown),
        }
    return {
        "schema_version": 2,
        "score_array_semantics": "seat_ordered_[seat0,seat1]",
        "cells": len(ordered),
        "delta_m": {
            "mean": statistics.fmean(deltas), "median": statistics.median(deltas),
            "positive": sum(delta > _EPS for delta in deltas),
            "negative": sum(delta < -_EPS for delta in deltas),
            "zero": sum(abs(delta) <= _EPS for delta in deltas),
            "worst_cell": _public_cell(worst), "best_cell": _public_cell(best),
            "supplied_mismatch_count": len(supplied_mismatches),
            "supplied_mismatches": supplied_mismatches,
        },
        "outcomes": {
            "baseline_wtl": dict(sorted(Counter(c["baseline_outcome"] for c in ordered).items())),
            "candidate_wtl": dict(sorted(Counter(c["candidate_outcome"] for c in ordered).items())),
            "transitions": dict(sorted(transitions.items())),
            "new_losses": new_losses, "lost_wins": lost_wins,
        },
        "by_seat": by_seat, "by_opponent": by_opponent, "activations": activation_summary,
    }


def policy_failures(report: Mapping[str, Any], *, require_no_new_losses: bool = False,
                    require_no_lost_wins: bool = False, min_mean_delta: float | None = None,
                    strict_supplied_delta: bool = False) -> list[str]:
    failures: list[str] = []
    if require_no_new_losses and report["outcomes"]["new_losses"]:
        failures.append(f'new losses: {len(report["outcomes"]["new_losses"])}')
    if require_no_lost_wins and report["outcomes"]["lost_wins"]:
        failures.append(f'lost wins: {len(report["outcomes"]["lost_wins"])}')
    if min_mean_delta is not None and report["delta_m"]["mean"] < min_mean_delta:
        failures.append(f'mean delta_m {report["delta_m"]["mean"]:.12g} < {min_mean_delta:.12g}')
    if strict_supplied_delta and report["delta_m"]["supplied_mismatch_count"]:
        failures.append(f'supplied delta_m mismatches: {report["delta_m"]["supplied_mismatch_count"]}')
    return failures


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataError(f"cannot read JSON evidence {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path, help="paired evaluator/bench JSON")
    parser.add_argument("--output", type=Path, help="also write the normalized report JSON")
    parser.add_argument("--require-no-new-losses", action="store_true")
    parser.add_argument("--require-no-lost-wins", action="store_true")
    parser.add_argument("--min-mean-delta", type=float)
    parser.add_argument("--strict-supplied-delta", action="store_true",
                        help="fail policy if a supplied delta field disagrees with recomputed scores")
    args = parser.parse_args(argv)
    try:
        if args.min_mean_delta is not None and not math.isfinite(args.min_mean_delta):
            raise DataError("--min-mean-delta must be finite")
        report = analyze(load_records(_read_json(args.evidence)))
    except DataError as exc:
        print(f"DATA ERROR: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    sys.stdout.write(rendered)
    if args.output:
        try:
            args.output.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            print(f"DATA ERROR: cannot write {args.output}: {exc}", file=sys.stderr)
            return 2
    failures = policy_failures(
        report,
        require_no_new_losses=args.require_no_new_losses,
        require_no_lost_wins=args.require_no_lost_wins,
        min_mean_delta=args.min_mean_delta,
        strict_supplied_delta=args.strict_supplied_delta,
    )
    if failures:
        for failure in failures:
            print("POLICY FAIL:", failure, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())