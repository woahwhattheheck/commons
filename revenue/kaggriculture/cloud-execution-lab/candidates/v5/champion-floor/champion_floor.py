#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed exact-V3.1 champion-floor economics authority for TITAN V5.

A V5 release can improve on the current release (for example V4) while still
remaining weaker than the submitted V3.1 champion.  This validator makes that
benchmark explicit: the control side is immutable exact submitted V3.1, while
the candidate side is one identified V5 build.  It authenticates raw matched
opponent/seed/seat scores, recomputes margins, and admits only a non-regressing
candidate on the complete balanced panel.

This module is evidence/control-plane only.  It does not execute gameplay,
change defaults, build archives, move release pointers, or submit to Kaggle.
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

SCHEMA = "titan-v5-v31-champion-floor/v1"
RECEIPT_SCHEMA = "titan-v5-v31-champion-floor-receipt/v1"
V31_SOURCE = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
V31_SUBMISSION_ID = 56172377
V31_ARCHIVE_SHA256 = "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"
MIN_OPPONENTS = 2
MIN_SEEDS = 4
MAX_INT = (1 << 63) - 1
_V5C_RE = re.compile(r"^v5c:[0-9a-f]{64}$")
_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_UNSET = object()
_REPORT_KEYS = frozenset(
    (
        "schema",
        "champion_source",
        "champion_submission_id",
        "champion_archive_sha256",
        "candidate_id",
        "candidate_archive_sha256",
        "engine_id",
        "opponent_pack_id",
        "cells",
    )
)
_CELL_KEYS = frozenset(
    (
        "opponent_id",
        "seed",
        "seat",
        "champion_own",
        "champion_rival",
        "candidate_own",
        "candidate_rival",
    )
)


class ChampionFloorError(ValueError):
    """Champion-floor evidence is malformed, cross-wired, or regressive."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ChampionFloorError(f"duplicate JSON object key: {key}")
        out[key] = value
    return out


def _reject_constant(token: str) -> None:
    raise ChampionFloorError(f"non-finite JSON constant is forbidden: {token}")


def _loads_strict(text: str, *, source: str = "<memory>") -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ChampionFloorError(f"{source}: invalid JSON: {exc.msg}") from exc


def _load_json(path: Path) -> tuple[Any, str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ChampionFloorError(f"cannot read champion-floor evidence: {path}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ChampionFloorError(f"champion-floor evidence is not UTF-8: {path}") from exc
    return _loads_strict(text, source=str(path)), hashlib.sha256(raw).hexdigest()


def _v5c(value: Any, field: str) -> str:
    if type(value) is not str or _V5C_RE.fullmatch(value) is None:
        raise ChampionFloorError(f"{field} must be v5c:<64 lowercase hex>")
    return value


def _hex40(value: Any, field: str) -> str:
    if type(value) is not str or _HEX40_RE.fullmatch(value) is None:
        raise ChampionFloorError(f"{field} must be 40 lowercase hex characters")
    return value


def _hex64(value: Any, field: str) -> str:
    if type(value) is not str or _HEX64_RE.fullmatch(value) is None:
        raise ChampionFloorError(f"{field} must be 64 lowercase hex characters")
    return value


def _nonempty_text(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise ChampionFloorError(f"{field} must be a non-empty string")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _nonempty_text(value, field)


def _plain_int(
    value: Any,
    field: str,
    *,
    minimum: int = 0,
    maximum: int = MAX_INT,
) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise ChampionFloorError(
            f"{field} must be a plain int in [{minimum}, {maximum}]"
        )
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _topology_sha256(keys: list[tuple[str, int, int]]) -> str:
    rows = [
        {"opponent_id": opponent_id, "seed": seed, "seat": seat}
        for opponent_id, seed, seat in keys
    ]
    return hashlib.sha256(_canonical_bytes(rows)).hexdigest()


def validate_report(
    report: Mapping[str, Any],
    *,
    candidate_id: str | None = None,
    candidate_archive_sha256: str | None = None,
    engine_id: str | None = None,
    opponent_pack_id: Any = _UNSET,
) -> dict[str, Any]:
    """Validate a balanced exact-V3.1-vs-candidate panel and return a receipt."""
    if type(report) is not dict:
        raise ChampionFloorError("champion-floor report must be an object")
    if set(report) != _REPORT_KEYS:
        missing = sorted(_REPORT_KEYS - set(report))
        extra = sorted(set(report) - _REPORT_KEYS)
        raise ChampionFloorError(
            f"champion-floor report keys mismatch; missing={missing!r} extra={extra!r}"
        )
    if report["schema"] != SCHEMA:
        raise ChampionFloorError(f"champion-floor report schema must be {SCHEMA}")

    source = _hex40(report["champion_source"], "champion_source")
    submission = _plain_int(
        report["champion_submission_id"], "champion_submission_id", minimum=1
    )
    champion_archive = _hex64(
        report["champion_archive_sha256"], "champion_archive_sha256"
    )
    if source != V31_SOURCE:
        raise ChampionFloorError("champion_source is not exact submitted V3.1")
    if submission != V31_SUBMISSION_ID:
        raise ChampionFloorError("champion_submission_id is not exact submitted V3.1")
    if champion_archive != V31_ARCHIVE_SHA256:
        raise ChampionFloorError("champion_archive_sha256 is not exact submitted V3.1")

    report_candidate = _v5c(report["candidate_id"], "candidate_id")
    candidate_archive = _hex64(
        report["candidate_archive_sha256"], "candidate_archive_sha256"
    )
    if candidate_archive == champion_archive:
        raise ChampionFloorError("candidate archive must differ from exact V3.1 archive")
    if candidate_id is not None and report_candidate != _v5c(
        candidate_id, "expected candidate_id"
    ):
        raise ChampionFloorError("candidate_id does not match release candidate")
    if candidate_archive_sha256 is not None and candidate_archive != _hex64(
        candidate_archive_sha256, "expected candidate_archive_sha256"
    ):
        raise ChampionFloorError("candidate archive does not match approved release")

    report_engine = _nonempty_text(report["engine_id"], "engine_id")
    if engine_id is not None and report_engine != _nonempty_text(engine_id, "expected engine_id"):
        raise ChampionFloorError("engine_id does not match candidate manifest")

    report_pack = _optional_text(report["opponent_pack_id"], "opponent_pack_id")
    if opponent_pack_id is not _UNSET:
        expected_pack = _optional_text(opponent_pack_id, "expected opponent_pack_id")
        if report_pack != expected_pack:
            raise ChampionFloorError("opponent_pack_id does not match candidate manifest")

    cells = report["cells"]
    if type(cells) is not list:
        raise ChampionFloorError("champion-floor cells must be a list")
    min_cells = MIN_OPPONENTS * MIN_SEEDS * 2
    if len(cells) < min_cells:
        raise ChampionFloorError(
            f"champion-floor panel requires at least {min_cells} cells"
        )

    keys: list[tuple[str, int, int]] = []
    deltas: list[int] = []
    champion_margins: list[int] = []
    candidate_margins: list[int] = []
    seats_by_opponent_seed: dict[tuple[str, int], set[int]] = {}
    seeds_by_opponent: dict[str, set[int]] = {}

    for index, cell in enumerate(cells):
        field = f"cells[{index}]"
        if type(cell) is not dict or set(cell) != _CELL_KEYS:
            raise ChampionFloorError(f"{field} must have exact raw score keys")
        opponent_id = _nonempty_text(cell["opponent_id"], f"{field}.opponent_id")
        seed = _plain_int(cell["seed"], f"{field}.seed")
        seat = _plain_int(cell["seat"], f"{field}.seat")
        if seat not in (0, 1):
            raise ChampionFloorError(f"{field}.seat must be exactly 0 or 1")
        key = (opponent_id, seed, seat)
        keys.append(key)
        seats_by_opponent_seed.setdefault((opponent_id, seed), set()).add(seat)
        seeds_by_opponent.setdefault(opponent_id, set()).add(seed)

        champion_own = _plain_int(cell["champion_own"], f"{field}.champion_own")
        champion_rival = _plain_int(cell["champion_rival"], f"{field}.champion_rival")
        candidate_own = _plain_int(cell["candidate_own"], f"{field}.candidate_own")
        candidate_rival = _plain_int(cell["candidate_rival"], f"{field}.candidate_rival")
        champion_margin = champion_own - champion_rival
        candidate_margin = candidate_own - candidate_rival
        champion_margins.append(champion_margin)
        candidate_margins.append(candidate_margin)
        deltas.append(candidate_margin - champion_margin)

    if len(keys) != len(set(keys)):
        raise ChampionFloorError("champion-floor opponent/seed/seat cells must be unique")
    if keys != sorted(keys):
        raise ChampionFloorError(
            "champion-floor cells must be canonically sorted by opponent_id, seed, then seat"
        )

    opponents = sorted(seeds_by_opponent)
    if len(opponents) < MIN_OPPONENTS:
        raise ChampionFloorError(
            f"champion-floor panel requires at least {MIN_OPPONENTS} distinct opponents"
        )
    reference_seeds = seeds_by_opponent[opponents[0]]
    if len(reference_seeds) < MIN_SEEDS:
        raise ChampionFloorError(
            f"champion-floor panel requires at least {MIN_SEEDS} distinct seeds per opponent"
        )
    unequal = [
        opponent
        for opponent in opponents[1:]
        if seeds_by_opponent[opponent] != reference_seeds
    ]
    if unequal:
        raise ChampionFloorError(
            "champion-floor opponents must cover identical seed sets; "
            f"mismatched={unequal!r}"
        )
    incomplete = sorted(
        (opponent, seed)
        for opponent in opponents
        for seed in sorted(reference_seeds)
        if seats_by_opponent_seed.get((opponent, seed)) != {0, 1}
    )
    if incomplete:
        raise ChampionFloorError(
            "champion-floor panel must contain exactly both seats for every opponent/seed; "
            f"incomplete={incomplete!r}"
        )
    expected_cells = len(opponents) * len(reference_seeds) * 2
    if len(cells) != expected_cells:
        raise ChampionFloorError(
            "champion-floor panel contains non-balanced opponent/seed/seat topology"
        )

    sum_delta = sum(deltas)
    if sum_delta < 0:
        raise ChampionFloorError(
            f"candidate regresses exact V3.1 champion: sum_delta={sum_delta} cells={len(cells)}"
        )
    mean_delta = sum_delta / len(cells)
    if not math.isfinite(mean_delta):
        raise ChampionFloorError("champion-floor mean margin delta is non-finite")

    positive = sum(delta > 0 for delta in deltas)
    negative = sum(delta < 0 for delta in deltas)
    tied = len(deltas) - positive - negative
    seeds = sorted(reference_seeds)
    return {
        "schema": RECEIPT_SCHEMA,
        "classification": "PASS",
        "promotion_ready": True,
        "champion_source": source,
        "champion_submission_id": submission,
        "champion_archive_sha256": champion_archive,
        "candidate_id": report_candidate,
        "candidate_archive_sha256": candidate_archive,
        "engine_id": report_engine,
        "opponent_pack_id": report_pack,
        "opponent_count": len(opponents),
        "opponent_ids": opponents,
        "seed_count": len(seeds),
        "seed_ids": seeds,
        "cell_count": len(cells),
        "sum_margin_delta": sum_delta,
        "mean_margin_delta": mean_delta,
        "positive_cells": positive,
        "negative_cells": negative,
        "tied_cells": tied,
        "champion_margin_sum": sum(champion_margins),
        "candidate_margin_sum": sum(candidate_margins),
        "topology_sha256": _topology_sha256(keys),
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
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report, _ = _load_json(args.report)
        receipt = validate_report(report)
        _atomic_emit(receipt, args.output)
    except (ChampionFloorError, OSError, TypeError, ValueError) as exc:
        print(f"champion_floor: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
