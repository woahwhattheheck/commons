#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Strict submitted-V3.1 competitive floor for TITAN V5 release transactions.

The generic paired economics gate proves that a candidate does not regress versus
its current control. That is necessary but not sufficient for the V4->V5 repair:
the owner acceptance target is strictly better than the exact submitted V3.1
champion. This sidecar validates a second raw panel on the *same* opponent, seed,
seat, and candidate-score cells and requires positive aggregate margin versus that
fixed historical floor.

It is intentionally release-control-plane only. The V3.1 identity is immutable and
hard-coded here so callers cannot silently choose an easier historical floor.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping

SCHEMA = "titan-v5-v31-floor/v1"
RECEIPT_SCHEMA = "titan-v5-v31-floor-receipt/v1"
FLOOR_ID = "kaggle-submission:56172377"
FLOOR_ARCHIVE_SHA256 = "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"
MAX_INT = (1 << 63) - 1
_V5C_RE = re.compile(r"^v5c:[0-9a-f]{64}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_UNSET = object()
_REPORT_KEYS = frozenset((
    "schema", "floor_id", "candidate_id", "engine_id", "opponent_pack_id",
    "floor_archive_sha256", "candidate_archive_sha256", "cells",
))
_CELL_KEYS = frozenset((
    "opponent_id", "seed", "seat", "floor_own", "floor_rival",
    "candidate_own", "candidate_rival",
))


class FloorError(ValueError):
    """Submitted-V3.1 floor evidence is malformed, cross-wired, or insufficient."""


def _v5c(value: Any, field: str) -> str:
    if type(value) is not str or _V5C_RE.fullmatch(value) is None:
        raise FloorError(f"{field} must be v5c:<64 lowercase hex>")
    return value


def _hex64(value: Any, field: str) -> str:
    if type(value) is not str or _HEX64_RE.fullmatch(value) is None:
        raise FloorError(f"{field} must be 64 lowercase hex characters")
    return value


def _text(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise FloorError(f"{field} must be a non-empty string")
    return value


def _opponent(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _plain_int(value: Any, field: str, *, maximum: int = MAX_INT) -> int:
    if type(value) is not int or value < 0 or value > maximum:
        raise FloorError(f"{field} must be a plain int in [0, {maximum}]")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def validate_report(
    report: Mapping[str, Any],
    economics_report: Mapping[str, Any],
    *,
    candidate_id: str | None = None,
    engine_id: str | None = None,
    opponent_pack_id: Any = _UNSET,
    candidate_archive_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate exact-V3.1 floor cells against the already-validated economics panel."""
    if type(report) is not dict or set(report) != _REPORT_KEYS:
        missing = sorted(_REPORT_KEYS - set(report)) if type(report) is dict else []
        extra = sorted(set(report) - _REPORT_KEYS) if type(report) is dict else []
        raise FloorError(f"V3.1 floor report keys mismatch; missing={missing!r} extra={extra!r}")
    if report["schema"] != SCHEMA:
        raise FloorError(f"V3.1 floor report schema must be {SCHEMA}")
    if type(economics_report) is not dict:
        raise FloorError("paired economics report must be an object")

    if report["floor_id"] != FLOOR_ID:
        raise FloorError(f"V3.1 floor_id must be exact authority {FLOOR_ID}")
    floor_archive = _hex64(report["floor_archive_sha256"], "V3.1 floor_archive_sha256")
    if floor_archive != FLOOR_ARCHIVE_SHA256:
        raise FloorError("V3.1 floor archive does not match exact submitted authority")

    report_candidate = _v5c(report["candidate_id"], "V3.1 floor candidate_id")
    if candidate_id is not None and report_candidate != _v5c(candidate_id, "expected candidate_id"):
        raise FloorError("V3.1 floor candidate_id does not match promotion candidate")
    if economics_report.get("candidate_id") != report_candidate:
        raise FloorError("V3.1 floor candidate_id disagrees with paired economics panel")

    report_engine = _text(report["engine_id"], "V3.1 floor engine_id")
    if engine_id is not None and report_engine != _text(engine_id, "expected engine_id"):
        raise FloorError("V3.1 floor engine_id does not match candidate manifest")
    if economics_report.get("engine_id") != report_engine:
        raise FloorError("V3.1 floor engine_id disagrees with paired economics panel")

    report_pack = _opponent(report["opponent_pack_id"], "V3.1 floor opponent_pack_id")
    if opponent_pack_id is not _UNSET:
        expected_pack = _opponent(opponent_pack_id, "expected opponent_pack_id")
        if report_pack != expected_pack:
            raise FloorError("V3.1 floor opponent_pack_id does not match candidate manifest")
    if economics_report.get("opponent_pack_id") != report_pack:
        raise FloorError("V3.1 floor opponent pack disagrees with paired economics panel")

    candidate_archive = _hex64(report["candidate_archive_sha256"], "V3.1 floor candidate_archive_sha256")
    if candidate_archive_sha256 is not None and candidate_archive != _hex64(
        candidate_archive_sha256, "expected candidate_archive_sha256"
    ):
        raise FloorError("V3.1 floor candidate archive does not match approved-new release")
    if economics_report.get("candidate_archive_sha256") != candidate_archive:
        raise FloorError("V3.1 floor candidate archive disagrees with paired economics panel")
    if candidate_archive == floor_archive:
        raise FloorError("candidate archive must differ from exact V3.1 floor archive")

    cells = report["cells"]
    economics_cells = economics_report.get("cells")
    if type(cells) is not list or type(economics_cells) is not list:
        raise FloorError("V3.1 floor and economics cells must both be lists")
    if len(cells) != len(economics_cells) or not cells:
        raise FloorError("V3.1 floor must use the exact paired-economics cell count")

    keys: list[tuple[str, int, int]] = []
    floor_margins: list[int] = []
    candidate_margins: list[int] = []
    candidate_rows: list[dict[str, Any]] = []
    for index, (cell, base_cell) in enumerate(zip(cells, economics_cells)):
        field = f"V3.1 floor cells[{index}]"
        if type(cell) is not dict or set(cell) != _CELL_KEYS:
            raise FloorError(f"{field} must have exact raw score keys")
        if type(base_cell) is not dict:
            raise FloorError(f"paired economics cells[{index}] must be an object")
        opponent = _text(cell["opponent_id"], f"{field}.opponent_id")
        seed = _plain_int(cell["seed"], f"{field}.seed")
        seat = _plain_int(cell["seat"], f"{field}.seat")
        if seat not in (0, 1):
            raise FloorError(f"{field}.seat must be exactly 0 or 1")
        key = (opponent, seed, seat)
        base_key = (base_cell.get("opponent_id"), base_cell.get("seed"), base_cell.get("seat"))
        if key != base_key:
            raise FloorError("V3.1 floor topology differs from paired economics panel")
        keys.append(key)

        floor_own = _plain_int(cell["floor_own"], f"{field}.floor_own")
        floor_rival = _plain_int(cell["floor_rival"], f"{field}.floor_rival")
        candidate_own = _plain_int(cell["candidate_own"], f"{field}.candidate_own")
        candidate_rival = _plain_int(cell["candidate_rival"], f"{field}.candidate_rival")
        if candidate_own != base_cell.get("candidate_own") or candidate_rival != base_cell.get("candidate_rival"):
            raise FloorError("V3.1 floor candidate scores differ from paired economics panel")
        floor_margins.append(floor_own - floor_rival)
        candidate_margins.append(candidate_own - candidate_rival)
        candidate_rows.append({
            "opponent_id": opponent, "seed": seed, "seat": seat,
            "candidate_own": candidate_own, "candidate_rival": candidate_rival,
        })

    if len(keys) != len(set(keys)):
        raise FloorError("V3.1 floor opponent/seed/seat cells must be unique")
    if keys != sorted(keys):
        raise FloorError("V3.1 floor cells must be canonically sorted")

    floor_delta_sum = sum(c - f for c, f in zip(candidate_margins, floor_margins))
    if floor_delta_sum <= 0:
        raise FloorError(
            "candidate must strictly outperform submitted V3.1 floor: "
            f"sum_delta={floor_delta_sum} cells={len(cells)}"
        )
    mean_delta = floor_delta_sum / len(cells)
    if not math.isfinite(mean_delta):
        raise FloorError("V3.1 floor mean margin delta is non-finite")

    opponents = sorted({key[0] for key in keys})
    seeds = sorted({key[1] for key in keys})
    return {
        "schema": RECEIPT_SCHEMA,
        "classification": "PASS",
        "release_ready": True,
        "floor_id": FLOOR_ID,
        "candidate_id": report_candidate,
        "engine_id": report_engine,
        "opponent_pack_id": report_pack,
        "floor_archive_sha256": floor_archive,
        "candidate_archive_sha256": candidate_archive,
        "opponent_count": len(opponents),
        "opponent_ids": opponents,
        "cell_count": len(cells),
        "seed_count": len(seeds),
        "floor_margin_sum": sum(floor_margins),
        "candidate_margin_sum": sum(candidate_margins),
        "sum_margin_delta_vs_v31": floor_delta_sum,
        "mean_margin_delta_vs_v31": mean_delta,
        "topology_sha256": hashlib.sha256(_canonical_bytes(keys)).hexdigest(),
        "candidate_scores_sha256": hashlib.sha256(_canonical_bytes(candidate_rows)).hexdigest(),
        "floor_panel_sha256": hashlib.sha256(_canonical_bytes(cells)).hexdigest(),
    }
