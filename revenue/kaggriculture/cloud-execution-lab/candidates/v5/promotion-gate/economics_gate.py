#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed paired competitive-economics authority for TITAN V5 releases.

The release pointer must not advance merely because a candidate is identifiable,
engaged, and fast.  This module authenticates a small raw paired panel and
recomputes the only policy asserted here: the candidate's mean paired margin
must not regress versus the exact control build.

Rows are intentionally primitive.  Each row carries the raw own/rival scores
for control and candidate at one exact (seed, seat) cell.  The validator derives
both margins and their delta itself; callers cannot smuggle a favorable summary.
Every seed must contain exactly both seats so seat imbalance cannot manufacture
a PASS.  The report order is canonical to make the evidence bytes reproducible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import uuid
from typing import Any, Mapping

SCHEMA = "titan-v5-paired-economics/v1"
RECEIPT_SCHEMA = "titan-v5-paired-economics-receipt/v1"
MIN_CELLS = 8
MIN_SEEDS = 4
_V5C_RE = re.compile(r"^v5c:[0-9a-f]{64}$")
_REPORT_KEYS = frozenset(("schema", "control_id", "candidate_id", "cells"))
_CELL_KEYS = frozenset(
    (
        "seed",
        "seat",
        "control_own",
        "control_rival",
        "candidate_own",
        "candidate_rival",
    )
)


class EconomicsError(ValueError):
    """Paired economics evidence is malformed, cross-wired, or regressive."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EconomicsError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> None:
    raise EconomicsError(f"non-finite JSON constant is forbidden: {token}")


def _loads_strict(text: str, *, source: str = "<memory>") -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise EconomicsError(f"{source}: invalid JSON: {exc.msg}") from exc


def _load_json(path: Path) -> tuple[Any, str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise EconomicsError(f"cannot read economics evidence: {path}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EconomicsError(f"economics evidence is not UTF-8: {path}") from exc
    return _loads_strict(text, source=str(path)), hashlib.sha256(raw).hexdigest()


def _v5c(value: Any, field: str) -> str:
    if type(value) is not str or _V5C_RE.fullmatch(value) is None:
        raise EconomicsError(f"{field} must be v5c:<64 lowercase hex>")
    return value


def _plain_int(value: Any, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise EconomicsError(f"{field} must be a plain int >= {minimum}")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def validate_report(
    report: Mapping[str, Any],
    *,
    candidate_id: str | None = None,
    control_id: str | None = None,
) -> dict[str, Any]:
    """Validate raw paired cells and return a deterministic no-regression receipt."""
    if type(report) is not dict:
        raise EconomicsError("economics report must be an object")
    if set(report) != _REPORT_KEYS:
        missing = sorted(_REPORT_KEYS - set(report))
        extra = sorted(set(report) - _REPORT_KEYS)
        raise EconomicsError(
            f"economics report keys mismatch; missing={missing!r} extra={extra!r}"
        )
    if report["schema"] != SCHEMA:
        raise EconomicsError(f"economics report schema must be {SCHEMA}")

    report_control = _v5c(report["control_id"], "economics control_id")
    report_candidate = _v5c(report["candidate_id"], "economics candidate_id")
    if report_control == report_candidate:
        raise EconomicsError("economics control_id and candidate_id must differ")
    if candidate_id is not None and report_candidate != _v5c(
        candidate_id, "expected candidate_id"
    ):
        raise EconomicsError("economics candidate_id does not match promotion candidate")
    if control_id is not None and report_control != _v5c(control_id, "expected control_id"):
        raise EconomicsError("economics control_id does not match promotion control")

    cells = report["cells"]
    if type(cells) is not list:
        raise EconomicsError("economics cells must be a list")
    if len(cells) < MIN_CELLS:
        raise EconomicsError(f"economics panel requires at least {MIN_CELLS} cells")

    keys: list[tuple[int, int]] = []
    deltas: list[int] = []
    control_margins: list[int] = []
    candidate_margins: list[int] = []
    seats_by_seed: dict[int, set[int]] = {}

    for index, cell in enumerate(cells):
        field = f"economics cells[{index}]"
        if type(cell) is not dict or set(cell) != _CELL_KEYS:
            raise EconomicsError(f"{field} must have exact raw score keys")
        seed = _plain_int(cell["seed"], f"{field}.seed")
        seat = _plain_int(cell["seat"], f"{field}.seat")
        if seat not in (0, 1):
            raise EconomicsError(f"{field}.seat must be exactly 0 or 1")
        key = (seed, seat)
        keys.append(key)
        seats_by_seed.setdefault(seed, set()).add(seat)

        control_own = _plain_int(cell["control_own"], f"{field}.control_own")
        control_rival = _plain_int(cell["control_rival"], f"{field}.control_rival")
        candidate_own = _plain_int(cell["candidate_own"], f"{field}.candidate_own")
        candidate_rival = _plain_int(cell["candidate_rival"], f"{field}.candidate_rival")
        control_margin = control_own - control_rival
        candidate_margin = candidate_own - candidate_rival
        control_margins.append(control_margin)
        candidate_margins.append(candidate_margin)
        deltas.append(candidate_margin - control_margin)

    if len(keys) != len(set(keys)):
        raise EconomicsError("economics seed/seat cells must be unique")
    if keys != sorted(keys):
        raise EconomicsError("economics cells must be canonically sorted by seed then seat")
    if len(seats_by_seed) < MIN_SEEDS:
        raise EconomicsError(f"economics panel requires at least {MIN_SEEDS} distinct seeds")
    incomplete = sorted(seed for seed, seats in seats_by_seed.items() if seats != {0, 1})
    if incomplete:
        raise EconomicsError(
            f"economics panel must contain exactly both seats for every seed; incomplete={incomplete!r}"
        )
    if len(cells) != 2 * len(seats_by_seed):
        raise EconomicsError("economics panel contains non-paired seed/seat topology")

    sum_delta = sum(deltas)
    if sum_delta < 0:
        raise EconomicsError(
            f"economics mean margin regresses: sum_delta={sum_delta} cells={len(cells)}"
        )

    positive = sum(delta > 0 for delta in deltas)
    negative = sum(delta < 0 for delta in deltas)
    tied = len(deltas) - positive - negative
    mean_delta = sum_delta / len(deltas)
    if not math.isfinite(mean_delta):
        raise EconomicsError("economics mean margin delta is non-finite")

    return {
        "schema": RECEIPT_SCHEMA,
        "classification": "PASS",
        "promotion_ready": True,
        "control_id": report_control,
        "candidate_id": report_candidate,
        "cell_count": len(cells),
        "seed_count": len(seats_by_seed),
        "sum_margin_delta": sum_delta,
        "mean_margin_delta": mean_delta,
        "positive_cells": positive,
        "negative_cells": negative,
        "tied_cells": tied,
        "control_margin_sum": sum(control_margins),
        "candidate_margin_sum": sum(candidate_margins),
        "panel_sha256": hashlib.sha256(_canonical_bytes(cells)).hexdigest(),
    }


def _atomic_emit(receipt: Mapping[str, Any], output: Path | None) -> None:
    payload = _canonical_bytes(receipt) + b"\n"
    if output is None:
        print(payload.decode("utf-8"), end="")
        return
    temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("economics_report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report, _ = _load_json(args.economics_report)
        receipt = validate_report(report)
        _atomic_emit(receipt, args.output)
    except (EconomicsError, OSError, TypeError, ValueError) as exc:
        print(f"economics_gate: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
