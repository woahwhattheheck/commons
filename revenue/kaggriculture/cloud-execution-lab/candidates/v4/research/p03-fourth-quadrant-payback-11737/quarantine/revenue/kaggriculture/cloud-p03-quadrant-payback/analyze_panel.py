#!/usr/bin/env python3
"""Strict disposition gate for P03 matched official-engine rows."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from quadrant_payback import ProjectedChain, certify_completion

OPPONENTS = ("current", "arlene", "retained")
SPLITS = ("development", "holdout")
SEATS = (0, 1)
REQUIRED_SEEDS_PER_SPLIT_AND_OPPONENT = 16


def _integer(row: Mapping[str, Any], key: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _load_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(value, dict) and isinstance(value.get("rows"), list):
        value = value["rows"]
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError("panel must be a JSON array/object.rows or JSONL objects")
    return value


def _validate_coverage(rows: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    seen: set[tuple[str, str, int, int]] = set()
    seeds: dict[tuple[str, str], set[int]] = defaultdict(set)
    seats_by_seed: dict[tuple[str, str, int], set[int]] = defaultdict(set)
    for row in rows:
        split = row.get("split")
        opponent = row.get("opponent")
        seed = _integer(row, "seed")
        seat = _integer(row, "seat")
        if split not in SPLITS:
            raise ValueError(f"unexpected split: {split!r}")
        if opponent not in OPPONENTS:
            raise ValueError(f"unexpected opponent: {opponent!r}")
        if seat not in SEATS:
            raise ValueError(f"unexpected seat: {seat!r}")
        identity = (str(split), str(opponent), seed, seat)
        if identity in seen:
            raise ValueError(f"duplicate result cell for {variant}: {identity}")
        seen.add(identity)
        seeds[(str(split), str(opponent))].add(seed)
        seats_by_seed[(str(split), str(opponent), seed)].add(seat)

    for split in SPLITS:
        for opponent in OPPONENTS:
            actual = seeds[(split, opponent)]
            if len(actual) != REQUIRED_SEEDS_PER_SPLIT_AND_OPPONENT:
                raise ValueError(
                    f"{variant} {split}/{opponent} has {len(actual)} seeds; "
                    f"expected {REQUIRED_SEEDS_PER_SPLIT_AND_OPPONENT}"
                )
            for seed in actual:
                if seats_by_seed[(split, opponent, seed)] != set(SEATS):
                    raise ValueError(
                        f"{variant} {split}/{opponent}/{seed} lacks both seats"
                    )

    development = set().union(*(seeds[("development", opponent)] for opponent in OPPONENTS))
    holdout = set().union(*(seeds[("holdout", opponent)] for opponent in OPPONENTS))
    overlap = sorted(development & holdout)
    if overlap:
        raise ValueError(f"development/holdout seed overlap for {variant}: {overlap}")
    expected_rows = len(OPPONENTS) * len(SPLITS) * len(SEATS) * REQUIRED_SEEDS_PER_SPLIT_AND_OPPONENT
    if len(rows) != expected_rows:
        raise ValueError(f"{variant} has {len(rows)} rows; expected {expected_rows}")
    return {
        "row_count": len(rows),
        "development_seed_count": len(development),
        "holdout_seed_count": len(holdout),
        "required_seeds_per_split_and_opponent": REQUIRED_SEEDS_PER_SPLIT_AND_OPPONENT,
    }


def analyze_variant(rows: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    coverage = _validate_coverage(rows, variant)
    deltas: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    split_totals: dict[str, int] = defaultdict(int)
    activation_count = 0
    certified_activations = 0
    decline_reasons: dict[str, int] = defaultdict(int)
    failures: list[str] = []

    for row in rows:
        candidate = _integer(row, "candidate_terminal_cash")
        control = _integer(row, "control_terminal_cash")
        if row.get("timeout") or row.get("error"):
            failures.append(
                f"runtime_failure:{row['split']}:{row['opponent']}:{row['seed']}:{row['seat']}"
            )
        if row.get("complete") is not True:
            failures.append(
                f"incomplete_game:{row['split']}:{row['opponent']}:{row['seed']}:{row['seat']}"
            )
        delta = candidate - control
        bucket = (str(row["split"]), str(row["opponent"]), int(row["seat"]))
        deltas[bucket].append(delta)
        split_totals[str(row["split"])] += delta

        activated = bool(row.get("activated", False))
        if not activated:
            continue
        activation_count += 1
        chain_value = row.get("chain")
        if not isinstance(chain_value, Mapping):
            failures.append(
                f"activation_missing_chain:{row['split']}:{row['opponent']}:{row['seed']}:{row['seat']}"
            )
            continue
        certificate = certify_completion(ProjectedChain.from_mapping(chain_value))
        if certificate.admitted:
            certified_activations += 1
        else:
            decline_reasons[certificate.reason] += 1
            failures.append(
                f"uncertified_activation:{certificate.reason}:{row['split']}:"
                f"{row['opponent']}:{row['seed']}:{row['seat']}"
            )

    bucket_summary: dict[str, dict[str, Any]] = {}
    heldout_nonnegative = True
    for (split, opponent, seat), values in sorted(deltas.items()):
        key = f"{split}/{opponent}/seat{seat}"
        total = sum(values)
        bucket_summary[key] = {
            "games": len(values),
            "terminal_cash_delta": total,
            "mean_terminal_cash_delta": total / len(values),
            "wins": sum(value > 0 for value in values),
            "ties": sum(value == 0 for value in values),
            "losses": sum(value < 0 for value in values),
        }
        if split == "holdout" and total < 0:
            heldout_nonnegative = False

    go = (
        not failures
        and activation_count > 0
        and certified_activations == activation_count
        and split_totals["development"] > 0
        and split_totals["holdout"] > 0
        and heldout_nonnegative
    )
    return {
        "variant": variant,
        "coverage": coverage,
        "activation_count": activation_count,
        "certified_activation_count": certified_activations,
        "certificate_declines": dict(sorted(decline_reasons.items())),
        "split_terminal_cash_delta": dict(sorted(split_totals.items())),
        "buckets": bucket_summary,
        "failures": failures,
        "disposition": "GO" if go else "HOLD",
    }


def analyze_panel(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in rows:
        row = dict(raw)
        variant = row.get("variant")
        if not isinstance(variant, str) or not variant:
            raise ValueError("each row requires a non-empty variant")
        grouped[variant].append(row)
    if not grouped:
        raise ValueError("empty panel")

    variants = [analyze_variant(grouped[name], name) for name in sorted(grouped)]
    go_variants = [item["variant"] for item in variants if item["disposition"] == "GO"]
    if len(go_variants) == 1:
        global_disposition = "GO"
        selected = go_variants[0]
    elif len(go_variants) > 1:
        global_disposition = "HOLD_MULTIPLE_GO_VARIANTS"
        selected = None
    else:
        global_disposition = "HOLD"
        selected = None
    return {
        "schema": "titan-p03-panel-disposition-v1",
        "variant_count": len(variants),
        "variants": variants,
        "go_variants": go_variants,
        "selected_variant": selected,
        "global_disposition": global_disposition,
        "canonical_enablement_authorized": global_disposition == "GO",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = analyze_panel(_load_rows(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
