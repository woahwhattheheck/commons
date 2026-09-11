#!/usr/bin/env python3
"""Fail-closed D3 externality merge gate for paired TITAN evaluator evidence.

This gate deliberately keeps two claims separate:

* terminal score externality: candidate-vs-baseline deltas in our score, rival score,
  and competitive margin; and
* product-price externality: trace evidence supplied as explicit per-cell events.

A terminal score change is not treated as proof of price causality. Product causality
is accepted only when the caller declares ``externality_complete: true`` and supplies
an exact per-cell coverage receipt plus any observed product events. Missing/incomplete
trace evidence yields HOLD, never PASS.

D3 hardens two evidence boundaries beyond the current parent reporter:

* every generic score vector, including top-level ``baseline_scores`` and
  ``candidate_scores``, is the pinned evaluator's player order ``[seat0, seat1]``;
* arm-pair input (``baseline`` + ``candidate``) may not coexist with a row-container
  alias (``cells``/``results``/``games``/``matches``), so representations cannot
  silently precedence-win over contradictory evidence.

Input extends the normal paired-evidence document with:

  "externality_complete": true,
  "externality_coverage": [
    {
      "opponent": "name", "seed": 123, "candidate_seat": 0,
      "source": "official_replay", "events_observed": 1
    }
  ],
  "externality_events": [
    {
      "event_id": "unique-id",
      "opponent": "name", "seed": 123, "candidate_seat": 0,
      "product": "WOOL", "source": "official_replay",
      "price_delta": 2, "rival_long_units": 4
    }
  ]

When completeness is asserted, coverage must contain exactly one receipt for every
paired cell and ``events_observed`` must equal the number of supplied events for that
cell. An empty event list is therefore acceptable only with explicit zero-event
coverage for every cell; a naked global completeness boolean can never PASS.

``price_delta`` means candidate quote minus baseline quote at the matched exposure
event. ``rival_long_units`` must be measured exposure, not inferred hidden inventory.
The conservative price-transfer proxy is max(price_delta, 0) * rival_long_units.

Exit codes: 0 PASS, 3 HOLD/BLOCK, 2 malformed evidence or CLI/data error.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Mapping, Sequence

import v31_delta_distribution_report as delta_report


class ExternalityError(ValueError):
    """Raised when D3-specific evidence is malformed or ambiguous."""


_MISSING = object()
_EPS = 1e-9
_ROW_CONTAINERS = ("cells", "results", "games", "matches")


def _number(value: Any, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExternalityError(f"{label} must be a JSON number")
    out = float(value)
    if not math.isfinite(out):
        raise ExternalityError(f"{label} must be finite")
    if nonnegative and out < 0:
        raise ExternalityError(f"{label} must be non-negative")
    return out


def _strict_nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ExternalityError(f"{label} must be a non-negative JSON integer")
    return value


def _strict_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ExternalityError(f"{label} must be a JSON boolean")
    return value


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExternalityError(f"{label} must be a non-empty string")
    return value.strip()


def _validate_document_representation(document: Any) -> None:
    """Reject ambiguous top-level evidence representations before parent normalization."""
    if not isinstance(document, Mapping):
        return
    arm_keys = [key for key in ("baseline", "candidate") if key in document]
    container_keys = [key for key in _ROW_CONTAINERS if key in document]
    if arm_keys and len(arm_keys) != 2:
        raise ExternalityError(
            "top-level arm evidence requires both baseline and candidate"
        )
    if arm_keys and container_keys:
        raise ExternalityError(
            "mixed arm-pair and row-container representations are ambiguous: "
            + ", ".join(arm_keys + container_keys)
        )


def _seat_ordered_pair(value: Any, label: str, seat: int) -> tuple[float, float]:
    """Decode the pinned official evaluator's [seat0, seat1] vector to (own, rival)."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise ExternalityError(f"{label} must contain player-ordered [seat0, seat1]")
    seat0 = _number(value[0], f"{label}[0]")
    seat1 = _number(value[1], f"{label}[1]")
    return (seat0, seat1) if seat == 0 else (seat1, seat0)


def _d3_arm_scores(
    record: Mapping[str, Any], arm: str, *, seat: int
) -> tuple[float, float]:
    """Normalize an arm while forcing top-level <arm>_scores to player order.

    The parent reporter currently normalizes nested ``scores`` in player order but
    treats top-level ``<arm>_scores`` as already candidate-relative. D3 cannot inherit
    that ambiguity because it directly gates rival externality. Decode the flat vector
    here, remove it before delegating all remaining alias/explicit-form checks to the
    parent, then require the two representations to agree when both are present.
    """
    flat_key = f"{arm}_scores"
    flat_pair = _MISSING
    stripped: Mapping[str, Any] = record
    if flat_key in record:
        flat_pair = _seat_ordered_pair(record[flat_key], flat_key, seat)
        mutable = dict(record)
        del mutable[flat_key]
        stripped = mutable

    other_pair = _MISSING
    try:
        other_pair = delta_report._arm_scores(stripped, arm, seat=seat)
    except delta_report.DataError as exc:
        if flat_pair is _MISSING or str(exc) != f"missing {arm} scores":
            raise

    if flat_pair is _MISSING:
        if other_pair is _MISSING:  # defensive; parent should have raised above
            raise delta_report.DataError(f"missing {arm} scores")
        return other_pair
    if other_pair is not _MISSING and other_pair != flat_pair:
        raise delta_report.DataError(
            f"conflicting {arm} score forms: {flat_key} vs other representation"
        )
    return flat_pair if other_pair is _MISSING else other_pair


def _paired_cells(document: Any) -> list[dict[str, Any]]:
    _validate_document_representation(document)
    records = delta_report.load_records(document)
    seen: set[tuple[str, str, int]] = set()
    cells: list[dict[str, Any]] = []
    for record in records:
        key = delta_report._cell_key(record)
        if key in seen:
            raise delta_report.DataError(f"duplicate logical cell: {key}")
        seen.add(key)
        baseline_own, baseline_rival = _d3_arm_scores(
            record, "baseline", seat=key[2]
        )
        candidate_own, candidate_rival = _d3_arm_scores(
            record, "candidate", seat=key[2]
        )
        delta_own = candidate_own - baseline_own
        delta_rival = candidate_rival - baseline_rival
        cells.append(
            {
                "opponent": key[0],
                "seed": key[1],
                "seat": key[2],
                "delta_own": delta_own,
                "delta_rival": delta_rival,
                "delta_m": delta_own - delta_rival,
            }
        )
    if not cells:
        raise delta_report.DataError("evidence cell list must be non-empty")
    return cells


def _event_key(event: Mapping[str, Any]) -> tuple[str, str, int]:
    return delta_report._cell_key(event)


def _trace_evidence(
    document: Any, valid_cells: set[tuple[str, str, int]]
) -> tuple[bool, list[dict[str, Any]], dict[str, Any]]:
    if not isinstance(document, Mapping):
        return False, [], {"receipts": 0, "all_cells_covered": False}

    complete_raw = document.get("externality_complete", _MISSING)
    complete = False if complete_raw is _MISSING else _strict_bool(
        complete_raw, "externality_complete"
    )

    raw_events = document.get("externality_events", [])
    if not isinstance(raw_events, list):
        raise ExternalityError("externality_events must be a JSON list")

    seen_ids: set[str] = set()
    events: list[dict[str, Any]] = []
    event_counts: Counter[tuple[str, str, int]] = Counter()
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, Mapping):
            raise ExternalityError(f"externality_events[{index}] must be an object")
        event_id = _nonempty_string(
            raw.get("event_id"), f"externality_events[{index}].event_id"
        )
        if event_id in seen_ids:
            raise ExternalityError(f"duplicate externality event_id: {event_id}")
        seen_ids.add(event_id)

        cell_key = _event_key(raw)
        if cell_key not in valid_cells:
            raise ExternalityError(
                f"externality event {event_id!r} references unknown paired cell {cell_key}"
            )
        product = _nonempty_string(raw.get("product"), f"{event_id}.product")
        source = _nonempty_string(raw.get("source"), f"{event_id}.source")
        price_delta = _number(raw.get("price_delta"), f"{event_id}.price_delta")
        rival_long_units = _number(
            raw.get("rival_long_units"), f"{event_id}.rival_long_units", nonnegative=True
        )
        uplift = max(0.0, price_delta) * rival_long_units
        event_counts[cell_key] += 1
        events.append(
            {
                "event_id": event_id,
                "opponent": cell_key[0],
                "seed": cell_key[1],
                "seat": cell_key[2],
                "product": product,
                "source": source,
                "price_delta": price_delta,
                "rival_long_units": rival_long_units,
                "estimated_rival_price_uplift": uplift,
            }
        )

    coverage = {"receipts": 0, "all_cells_covered": False}
    if not complete:
        return False, events, coverage

    raw_coverage = document.get("externality_coverage", _MISSING)
    if not isinstance(raw_coverage, list):
        raise ExternalityError(
            "externality_complete=true requires externality_coverage list"
        )

    seen_cells: set[tuple[str, str, int]] = set()
    for index, raw in enumerate(raw_coverage):
        if not isinstance(raw, Mapping):
            raise ExternalityError(f"externality_coverage[{index}] must be an object")
        cell_key = _event_key(raw)
        if cell_key not in valid_cells:
            raise ExternalityError(
                f"externality coverage references unknown paired cell {cell_key}"
            )
        if cell_key in seen_cells:
            raise ExternalityError(f"duplicate externality coverage cell: {cell_key}")
        seen_cells.add(cell_key)
        _nonempty_string(raw.get("source"), f"externality_coverage[{index}].source")
        observed = _strict_nonnegative_int(
            raw.get("events_observed"),
            f"externality_coverage[{index}].events_observed",
        )
        actual = event_counts.get(cell_key, 0)
        if observed != actual:
            raise ExternalityError(
                f"externality coverage event count mismatch for {cell_key}: "
                f"receipt={observed} events={actual}"
            )

    if seen_cells != valid_cells:
        missing = sorted(valid_cells - seen_cells)
        extra = sorted(seen_cells - valid_cells)
        raise ExternalityError(
            "externality coverage must contain exactly one receipt per paired cell; "
            f"missing={missing[:5]} extra={extra[:5]}"
        )

    coverage = {"receipts": len(seen_cells), "all_cells_covered": True}
    return True, events, coverage


def evaluate(
    document: Any,
    *,
    min_mean_delta_m: float = 0.0,
    max_mean_delta_rival: float = 0.0,
    max_total_price_uplift: float = 0.0,
) -> dict[str, Any]:
    min_mean_delta_m = _number(min_mean_delta_m, "min_mean_delta_m")
    max_mean_delta_rival = _number(max_mean_delta_rival, "max_mean_delta_rival")
    max_total_price_uplift = _number(
        max_total_price_uplift, "max_total_price_uplift", nonnegative=True
    )

    cells = _paired_cells(document)
    valid_cells = {(c["opponent"], c["seed"], c["seat"]) for c in cells}
    trace_complete, events, coverage = _trace_evidence(document, valid_cells)

    mean_delta_own = statistics.fmean(c["delta_own"] for c in cells)
    mean_delta_rival = statistics.fmean(c["delta_rival"] for c in cells)
    mean_delta_m = statistics.fmean(c["delta_m"] for c in cells)

    by_product: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[event["product"]].append(event)
    for product in sorted(grouped):
        product_events = grouped[product]
        by_product[product] = {
            "events": len(product_events),
            "positive_price_events": sum(e["price_delta"] > _EPS for e in product_events),
            "rival_long_events": sum(e["rival_long_units"] > _EPS for e in product_events),
            "estimated_rival_price_uplift": sum(
                e["estimated_rival_price_uplift"] for e in product_events
            ),
        }

    total_price_uplift = sum(e["estimated_rival_price_uplift"] for e in events)
    reasons: list[str] = []
    verdict = "PASS"

    if not trace_complete:
        verdict = "HOLD"
        reasons.append("product externality trace is not declared complete")

    if mean_delta_m <= min_mean_delta_m + _EPS:
        verdict = "BLOCK"
        reasons.append(
            f"mean delta margin {mean_delta_m:.6g} is not above required "
            f"{min_mean_delta_m:.6g}"
        )
    if mean_delta_rival > max_mean_delta_rival + _EPS:
        verdict = "BLOCK"
        reasons.append(
            f"mean rival delta {mean_delta_rival:.6g} exceeds allowed "
            f"{max_mean_delta_rival:.6g}"
        )
    if total_price_uplift > max_total_price_uplift + _EPS:
        verdict = "BLOCK"
        reasons.append(
            f"measured rival price-uplift proxy {total_price_uplift:.6g} exceeds allowed "
            f"{max_total_price_uplift:.6g}"
        )

    return {
        "schema": "titan-v31-d3-externality-gate-v2",
        "verdict": verdict,
        "reasons": reasons,
        "cells": len(cells),
        "trace_complete": trace_complete,
        "trace_coverage": coverage,
        "terminal": {
            "mean_delta_own": mean_delta_own,
            "mean_delta_rival": mean_delta_rival,
            "mean_delta_m": mean_delta_m,
        },
        "product_externality": {
            "events": len(events),
            "estimated_rival_price_uplift": total_price_uplift,
            "by_product": by_product,
        },
        "policy": {
            "min_mean_delta_m": min_mean_delta_m,
            "max_mean_delta_rival": max_mean_delta_rival,
            "max_total_price_uplift": max_total_price_uplift,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="paired evaluator JSON evidence")
    parser.add_argument("--min-mean-delta-m", type=float, default=0.0)
    parser.add_argument("--max-mean-delta-rival", type=float, default=0.0)
    parser.add_argument("--max-total-price-uplift", type=float, default=0.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
        report = evaluate(
            document,
            min_mean_delta_m=args.min_mean_delta_m,
            max_mean_delta_rival=args.max_mean_delta_rival,
            max_total_price_uplift=args.max_total_price_uplift,
        )
    except (OSError, json.JSONDecodeError, delta_report.DataError, ExternalityError) as exc:
        print(f"D3_DATA_ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["verdict"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
