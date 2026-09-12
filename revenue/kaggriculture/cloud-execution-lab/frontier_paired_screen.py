#!/usr/bin/env python3
"""Promotion-safe paired evidence for TITAN V5 simulation screens.

The analyzer deliberately does not author candidate or opponent identity. Callers
should pass opaque identities produced by the experiment-identity and opponent
pack tooling. Results are only compared on exact (opponent, seed, seat) cells.

Examples:
    python frontier_paired_screen.py rows.jsonl \
        --baseline base-id --candidate challenger-id --expected expected.json
    python frontier_paired_screen.py rows.jsonl \
        --baseline base-id --a a-id --b b-id --ab ab-id --expected expected.json

`promotion_ready` is never true without a declared expected design and complete
scored coverage for every relevant variant.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable, Mapping, Sequence

Cell = tuple[str, int, int]


class EvidenceError(ValueError):
    """Raised when simulation evidence is malformed or ambiguous."""


def _plain_int(value: object, *, field: str) -> int:
    if type(value) is not int:
        raise EvidenceError(f"{field} must be a plain integer")
    return value


def _identity(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise EvidenceError(f"{field} must not have surrounding whitespace")
    return value


def _finite_number(value: object, *, field: str) -> float:
    if type(value) not in (int, float):
        raise EvidenceError(f"{field} must be a finite number")
    out = float(value)
    if not math.isfinite(out):
        raise EvidenceError(f"{field} must be a finite number")
    return out


def _cell_from_mapping(value: Mapping[str, object], *, field: str) -> Cell:
    opponent = _identity(value.get("opponent"), field=f"{field}.opponent")
    seed = _plain_int(value.get("seed"), field=f"{field}.seed")
    seat = _plain_int(value.get("seat"), field=f"{field}.seat")
    if seat not in (0, 1):
        raise EvidenceError(f"{field}.seat must be 0 or 1")
    return opponent, seed, seat


def _cell_json(cell: Cell) -> dict[str, object]:
    opponent, seed, seat = cell
    return {"opponent": opponent, "seed": seed, "seat": seat}


def _cell_sort_key(cell: Cell) -> tuple[str, int, int]:
    return cell


def _margin(row: Mapping[str, object], *, row_number: int) -> float:
    explicit = row.get("margin")
    has_explicit = explicit is not None
    has_candidate_score = row.get("candidate_score") is not None
    has_opponent_score = row.get("opponent_score") is not None

    score_margin: float | None = None
    if has_candidate_score or has_opponent_score:
        if not (has_candidate_score and has_opponent_score):
            raise EvidenceError(
                f"row {row_number} must provide candidate_score and opponent_score together"
            )
        candidate_score = _finite_number(
            row.get("candidate_score"), field=f"row {row_number}.candidate_score"
        )
        opponent_score = _finite_number(
            row.get("opponent_score"), field=f"row {row_number}.opponent_score"
        )
        score_margin = candidate_score - opponent_score

    if has_explicit:
        margin = _finite_number(explicit, field=f"row {row_number}.margin")
        if score_margin is not None and not math.isclose(
            margin, score_margin, rel_tol=0.0, abs_tol=1e-9
        ):
            raise EvidenceError(
                f"row {row_number} margin disagrees with candidate/opponent scores"
            )
        return margin
    if score_margin is not None:
        return score_margin
    raise EvidenceError(
        f"row {row_number} complete result needs margin or candidate_score+opponent_score"
    )


def _normalize_rows(
    rows: Iterable[Mapping[str, object]],
) -> tuple[
    dict[str, dict[Cell, float]],
    dict[str, dict[Cell, str]],
]:
    complete: dict[str, dict[Cell, float]] = {}
    incomplete: dict[str, dict[Cell, str]] = {}
    seen: set[tuple[str, Cell]] = set()

    for row_number, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            raise EvidenceError(f"row {row_number} must be an object")
        variant = _identity(row.get("variant"), field=f"row {row_number}.variant")
        cell = _cell_from_mapping(row, field=f"row {row_number}")
        key = variant, cell
        if key in seen:
            raise EvidenceError(
                f"duplicate result for variant={variant!r}, cell={_cell_json(cell)!r}"
            )
        seen.add(key)

        raw_status = row.get("status")
        if raw_status is None:
            status = "complete"
        else:
            status = _identity(raw_status, field=f"row {row_number}.status")

        if status == "complete":
            complete.setdefault(variant, {})[cell] = _margin(
                row, row_number=row_number
            )
        else:
            incomplete.setdefault(variant, {})[cell] = status

    return complete, incomplete


def _normalize_expected(
    expected_cells: Sequence[Mapping[str, object]] | None,
) -> tuple[Cell, ...] | None:
    if expected_cells is None:
        return None
    if isinstance(expected_cells, (str, bytes)) or not isinstance(
        expected_cells, Sequence
    ):
        raise EvidenceError("expected cells must be a list")
    cells: list[Cell] = []
    seen: set[Cell] = set()
    for index, value in enumerate(expected_cells, 1):
        if not isinstance(value, Mapping):
            raise EvidenceError(f"expected cell {index} must be an object")
        cell = _cell_from_mapping(value, field=f"expected cell {index}")
        if cell in seen:
            raise EvidenceError(f"duplicate expected cell {_cell_json(cell)!r}")
        seen.add(cell)
        cells.append(cell)
    if not cells:
        raise EvidenceError("expected cells must not be empty")
    cells.sort(key=_cell_sort_key)
    return tuple(cells)


def _variant_gaps(
    *,
    variant: str,
    design: Sequence[Cell],
    complete: Mapping[str, Mapping[Cell, float]],
    incomplete: Mapping[str, Mapping[Cell, str]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    scored = complete.get(variant, {})
    failed = incomplete.get(variant, {})
    missing: list[dict[str, object]] = []
    blocked: list[dict[str, object]] = []
    for cell in design:
        if cell in scored:
            continue
        if cell in failed:
            blocked.append({**_cell_json(cell), "status": failed[cell]})
        else:
            missing.append(_cell_json(cell))
    return missing, blocked


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def paired_summary(
    rows: Iterable[Mapping[str, object]],
    *,
    baseline: str,
    candidate: str,
    expected_cells: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Return exact-cell candidate-vs-baseline paired evidence."""
    baseline = _identity(baseline, field="baseline")
    candidate = _identity(candidate, field="candidate")
    if baseline == candidate:
        raise EvidenceError("baseline and candidate must be different")

    complete, incomplete = _normalize_rows(rows)
    expected = _normalize_expected(expected_cells)
    base_scores = complete.get(baseline, {})
    candidate_scores = complete.get(candidate, {})

    if expected is None:
        paired_cells = sorted(
            set(base_scores).intersection(candidate_scores), key=_cell_sort_key
        )
        design: Sequence[Cell] = paired_cells
    else:
        design = expected
        paired_cells = [
            cell
            for cell in expected
            if cell in base_scores and cell in candidate_scores
        ]

    deltas = [candidate_scores[cell] - base_scores[cell] for cell in paired_cells]
    missing_base, incomplete_base = _variant_gaps(
        variant=baseline,
        design=design,
        complete=complete,
        incomplete=incomplete,
    )
    missing_candidate, incomplete_candidate = _variant_gaps(
        variant=candidate,
        design=design,
        complete=complete,
        incomplete=incomplete,
    )

    promotion_ready = (
        expected is not None
        and len(paired_cells) == len(expected)
        and not missing_base
        and not missing_candidate
        and not incomplete_base
        and not incomplete_candidate
    )

    return {
        "schema": "titan-v5-paired-screen-v1",
        "mode": "paired",
        "baseline": baseline,
        "candidate": candidate,
        "expected_declared": expected is not None,
        "expected_n": len(expected) if expected is not None else None,
        "paired_n": len(paired_cells),
        "paired_mean_delta": _mean(deltas),
        "promotion_ready": promotion_ready,
        "paired_deltas": [
            {**_cell_json(cell), "delta": delta}
            for cell, delta in zip(paired_cells, deltas)
        ],
        "missing": {
            baseline: missing_base,
            candidate: missing_candidate,
        },
        "incomplete": {
            baseline: incomplete_base,
            candidate: incomplete_candidate,
        },
    }


def interaction_summary(
    rows: Iterable[Mapping[str, object]],
    *,
    baseline: str,
    a: str,
    b: str,
    ab: str,
    expected_cells: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Return exact-cell 2x2 interaction evidence for baseline/A/B/A+B."""
    names = {
        "baseline": _identity(baseline, field="baseline"),
        "a": _identity(a, field="a"),
        "b": _identity(b, field="b"),
        "ab": _identity(ab, field="ab"),
    }
    if len(set(names.values())) != 4:
        raise EvidenceError("baseline, a, b, and ab must be four distinct variants")

    complete, incomplete = _normalize_rows(rows)
    expected = _normalize_expected(expected_cells)
    score_maps = {name: complete.get(variant, {}) for name, variant in names.items()}

    if expected is None:
        common = set.intersection(
            *(set(score_map) for score_map in score_maps.values())
        )
        cells = sorted(common, key=_cell_sort_key)
        design: Sequence[Cell] = cells
    else:
        design = expected
        cells = [
            cell
            for cell in expected
            if all(cell in score_map for score_map in score_maps.values())
        ]

    interactions: list[float] = []
    component_deltas: dict[str, list[float]] = {"a": [], "b": [], "ab": []}
    per_cell: list[dict[str, object]] = []
    for cell in cells:
        base_value = score_maps["baseline"][cell]
        a_value = score_maps["a"][cell]
        b_value = score_maps["b"][cell]
        ab_value = score_maps["ab"][cell]
        interaction = ab_value - a_value - b_value + base_value
        interactions.append(interaction)
        component_deltas["a"].append(a_value - base_value)
        component_deltas["b"].append(b_value - base_value)
        component_deltas["ab"].append(ab_value - base_value)
        per_cell.append(
            {
                **_cell_json(cell),
                "a_delta": a_value - base_value,
                "b_delta": b_value - base_value,
                "ab_delta": ab_value - base_value,
                "interaction": interaction,
            }
        )

    missing: dict[str, list[dict[str, object]]] = {}
    blocked: dict[str, list[dict[str, object]]] = {}
    for label, variant in names.items():
        missing[variant], blocked[variant] = _variant_gaps(
            variant=variant,
            design=design,
            complete=complete,
            incomplete=incomplete,
        )

    promotion_ready = (
        expected is not None
        and len(cells) == len(expected)
        and all(not items for items in missing.values())
        and all(not items for items in blocked.values())
    )

    return {
        "schema": "titan-v5-paired-screen-v1",
        "mode": "interaction_2x2",
        "variants": names,
        "expected_declared": expected is not None,
        "expected_n": len(expected) if expected is not None else None,
        "quadruple_n": len(cells),
        "paired_mean_deltas": {
            label: _mean(values) for label, values in component_deltas.items()
        },
        "mean_interaction": _mean(interactions),
        "promotion_ready": promotion_ready,
        "cells": per_cell,
        "missing": missing,
        "incomplete": blocked,
    }


def _load_jsonl(path: Path) -> list[Mapping[str, object]]:
    rows: list[Mapping[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvidenceError(
                    f"{path}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            if not isinstance(value, dict):
                raise EvidenceError(f"{path}:{line_number}: row must be an object")
            rows.append(value)
    if not rows:
        raise EvidenceError(f"{path}: no result rows")
    return rows


def _load_expected(path: Path | None) -> Sequence[Mapping[str, object]] | None:
    if path is None:
        return None
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if isinstance(value, dict):
        value = value.get("cells")
    if not isinstance(value, list):
        raise EvidenceError("expected file must be a JSON list or {'cells': [...]} object")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=Path, help="JSONL result rows")
    parser.add_argument("--expected", type=Path, help="declared expected-cell JSON")
    parser.add_argument("--baseline", required=True, help="opaque baseline candidate identity")
    parser.add_argument("--candidate", help="opaque candidate identity for paired mode")
    parser.add_argument("--a", help="A identity for 2x2 mode")
    parser.add_argument("--b", help="B identity for 2x2 mode")
    parser.add_argument("--ab", help="A+B identity for 2x2 mode")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    interaction_args = (args.a, args.b, args.ab)
    paired_mode = args.candidate is not None and not any(interaction_args)
    interaction_mode = args.candidate is None and all(
        value is not None for value in interaction_args
    )
    if not (paired_mode or interaction_mode):
        parser.error(
            "choose exactly one mode: --candidate, or the full --a/--b/--ab set"
        )

    try:
        rows = _load_jsonl(args.rows)
        expected = _load_expected(args.expected)
        if paired_mode:
            report = paired_summary(
                rows,
                baseline=args.baseline,
                candidate=args.candidate,
                expected_cells=expected,
            )
        else:
            report = interaction_summary(
                rows,
                baseline=args.baseline,
                a=args.a,
                b=args.b,
                ab=args.ab,
                expected_cells=expected,
            )
    except (OSError, json.JSONDecodeError, EvidenceError) as exc:
        parser.error(str(exc))

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
