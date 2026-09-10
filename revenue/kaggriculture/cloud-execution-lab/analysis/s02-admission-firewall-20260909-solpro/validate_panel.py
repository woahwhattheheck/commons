# SPDX-License-Identifier: Apache-2.0
"""Fail-closed paired-panel validator for TITAN planner candidates."""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

PairKey = tuple[str, int, int]
_ALLOWED_VARIANTS = frozenset(("baseline", "candidate"))


@dataclass(frozen=True)
class PanelVerdict:
    admitted: bool
    reasons: tuple[str, ...]
    schedule_bound: bool
    scheduled_pairs: int
    observed_pairs: int
    complete_pairs: int
    baseline_wtl: tuple[int, int, int]
    candidate_wtl: tuple[int, int, int]
    mean_margin_delta: float | None
    worst_margin_delta: float | None
    seats: tuple[int, ...]
    opponents: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _pair_key(row: dict[str, Any]) -> PairKey:
    return str(row["opponent"]), int(row["seed"]), int(row["candidate_seat"])


def _own_margin(row: dict[str, Any]) -> float:
    scores = row.get("scores")
    seat = int(row["candidate_seat"])
    if not isinstance(scores, list) or len(scores) != 2 or seat not in (0, 1):
        raise ValueError("invalid scores/seat")
    own = float(scores[seat])
    rival = float(scores[1 - seat])
    if not math.isfinite(own) or not math.isfinite(rival):
        raise ValueError("non-finite score")
    return own - rival


def _wtl(margins: Iterable[float]) -> tuple[int, int, int]:
    wins = ties = losses = 0
    for margin in margins:
        if margin > 0:
            wins += 1
        elif margin < 0:
            losses += 1
        else:
            ties += 1
    return wins, ties, losses


def _normalize_expected(expected_pairs: Iterable[PairKey] | None) -> tuple[PairKey, ...] | None:
    if expected_pairs is None:
        return None
    normalized: list[PairKey] = []
    for opponent, seed, seat in expected_pairs:
        key = str(opponent), int(seed), int(seat)
        if key[2] not in (0, 1):
            raise ValueError(f"invalid expected seat: {key[2]}")
        normalized.append(key)
    if len(set(normalized)) != len(normalized):
        raise ValueError("duplicate expected pair")
    return tuple(sorted(normalized))


def validate_rows(
    rows: list[dict[str, Any]],
    *,
    expected_pairs: Iterable[PairKey] | None = None,
    required_seats: tuple[int, ...] = (0, 1),
    min_pairs: int = 32,
    min_mean_margin_delta: float = 0.0,
    max_worst_margin_regression: float = 0.0,
) -> PanelVerdict:
    """Validate an exact matched schedule.

    Admission always requires ``expected_pairs``. Without a schedule manifest,
    a panel cannot prove that a baseline/candidate pair was omitted entirely.
    Diagnostic metrics are still returned, but the verdict fails closed with
    ``schedule_unbound``.
    """
    reasons: list[str] = []
    expected = _normalize_expected(expected_pairs)
    if expected is None:
        reasons.append("schedule_unbound")

    keyed: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    duplicates: list[tuple[str, int, int, str]] = []
    observed_pair_keys: set[PairKey] = set()
    unexpected_variants = 0
    malformed = 0
    for row in rows:
        try:
            variant = str(row["variant"])
            pair = _pair_key(row)
        except (KeyError, TypeError, ValueError):
            malformed += 1
            continue
        if variant not in _ALLOWED_VARIANTS:
            unexpected_variants += 1
            continue
        key = (*pair, variant)
        observed_pair_keys.add(pair)
        if key in keyed:
            duplicates.append(key)
        keyed[key] = row
    if malformed:
        reasons.append(f"malformed_identity:{malformed}")
    if unexpected_variants:
        reasons.append(f"unexpected_variants:{unexpected_variants}")
    if duplicates:
        reasons.append(f"duplicate_rows:{len(duplicates)}")

    expected_set = set(expected or ())
    if expected is None:
        scheduled_pair_keys = set(observed_pair_keys)
    else:
        missing_expected = expected_set - observed_pair_keys
        unexpected_pairs = observed_pair_keys - expected_set
        if missing_expected:
            reasons.append(f"missing_expected_pairs:{len(missing_expected)}")
        if unexpected_pairs:
            reasons.append(f"unexpected_pairs:{len(unexpected_pairs)}")
        scheduled_pair_keys = expected_set

    complete: list[tuple[dict[str, Any], dict[str, Any]]] = []
    missing_rows = 0
    noncomplete = 0
    invalid = 0
    for opponent, seed, seat in sorted(scheduled_pair_keys):
        baseline = keyed.get((opponent, seed, seat, "baseline"))
        candidate = keyed.get((opponent, seed, seat, "candidate"))
        if baseline is None or candidate is None:
            missing_rows += int(baseline is None) + int(candidate is None)
            continue
        if baseline.get("status") != "complete" or candidate.get("status") != "complete":
            noncomplete += 1
            continue
        try:
            _own_margin(baseline)
            _own_margin(candidate)
        except (KeyError, TypeError, ValueError, IndexError):
            invalid += 1
            continue
        complete.append((baseline, candidate))
    if missing_rows:
        reasons.append(f"missing_variant_rows:{missing_rows}")
    if noncomplete:
        reasons.append(f"noncomplete_pairs:{noncomplete}")
    if invalid:
        reasons.append(f"invalid_score_pairs:{invalid}")
    if len(complete) < int(min_pairs):
        reasons.append(f"insufficient_pairs:{len(complete)}<{int(min_pairs)}")

    seats = tuple(sorted({int(base["candidate_seat"]) for base, _ in complete}))
    if any(seat not in seats for seat in required_seats):
        reasons.append(f"missing_required_seat:{required_seats}")
    opponents = tuple(sorted({str(base["opponent"]) for base, _ in complete}))
    if not opponents:
        reasons.append("no_opponents")

    baseline_margins = [_own_margin(base) for base, _ in complete]
    candidate_margins = [_own_margin(candidate) for _, candidate in complete]
    deltas = [candidate - baseline for baseline, candidate in zip(baseline_margins, candidate_margins)]
    baseline_wtl = _wtl(baseline_margins)
    candidate_wtl = _wtl(candidate_margins)
    mean_delta = sum(deltas) / len(deltas) if deltas else None
    worst_delta = min(deltas) if deltas else None
    if mean_delta is None or mean_delta < float(min_mean_margin_delta):
        reasons.append(f"mean_margin_delta:{mean_delta}<{float(min_mean_margin_delta)}")
    if worst_delta is None or worst_delta < -float(max_worst_margin_regression):
        reasons.append(f"worst_margin_delta:{worst_delta}<-{float(max_worst_margin_regression)}")
    if candidate_wtl[2] > baseline_wtl[2]:
        reasons.append(f"losses_increased:{candidate_wtl[2]}>{baseline_wtl[2]}")
    if candidate_wtl[0] < baseline_wtl[0]:
        reasons.append(f"wins_decreased:{candidate_wtl[0]}<{baseline_wtl[0]}")

    # Preserve first-occurrence order while avoiding noisy duplicate reasons.
    unique_reasons = tuple(dict.fromkeys(reasons))
    return PanelVerdict(
        admitted=not unique_reasons,
        reasons=unique_reasons,
        schedule_bound=expected is not None,
        scheduled_pairs=len(scheduled_pair_keys),
        observed_pairs=len(observed_pair_keys),
        complete_pairs=len(complete),
        baseline_wtl=baseline_wtl,
        candidate_wtl=candidate_wtl,
        mean_margin_delta=mean_delta,
        worst_margin_delta=worst_delta,
        seats=seats,
        opponents=opponents,
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"line {number} is not an object")
        rows.append(value)
    return rows


def load_schedule(path: Path) -> tuple[PairKey, ...]:
    value = json.loads(path.read_text(encoding="utf-8"))
    pairs = value.get("pairs") if isinstance(value, dict) else value
    if not isinstance(pairs, list):
        raise ValueError("schedule must be a list or an object containing a pairs list")
    parsed: list[PairKey] = []
    for index, row in enumerate(pairs):
        if not isinstance(row, dict):
            raise ValueError(f"schedule pair {index} is not an object")
        try:
            parsed.append(_pair_key(row))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid schedule pair {index}") from exc
    normalized = _normalize_expected(parsed)
    assert normalized is not None
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("panel", type=Path)
    parser.add_argument("--schedule", type=Path)
    parser.add_argument("--min-pairs", type=int, default=32)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    expected = load_schedule(args.schedule) if args.schedule else None
    verdict = validate_rows(
        load_jsonl(args.panel), expected_pairs=expected, min_pairs=args.min_pairs
    )
    rendered = json.dumps(verdict.to_dict(), indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if verdict.admitted else 2


if __name__ == "__main__":
    raise SystemExit(main())
