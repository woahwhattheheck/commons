#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed TITAN V5 champion ratchet against exact submitted V3.1.

This gate is evidence-only. It does not execute gameplay or move a release
pointer. It authenticates one balanced raw panel containing incumbent, exact
V3.1 champion, and candidate outcomes on identical opponent/seed/seat cells.

The candidate must be non-regressive versus the incumbent and must strictly
clear V3.1 on the leaderboard-facing own-score objective. Margin and no-new-loss
guards prevent an own-score gain from buying systematically worse competitive
outcomes.
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

SCHEMA = "titan-v5-champion-ratchet/v1"
RECEIPT_SCHEMA = "titan-v5-champion-ratchet-receipt/v1"
V31_ARCHIVE_SHA256 = "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"
MIN_OPPONENTS = 2
MIN_SEEDS = 4
MAX_INT = (1 << 63) - 1
_V5C = re.compile(r"^v5c:[0-9a-f]{64}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_REPORT_KEYS = frozenset({
    "schema", "incumbent_id", "candidate_id", "engine_id", "opponent_pack_id",
    "incumbent_archive_sha256", "champion_archive_sha256", "candidate_archive_sha256",
    "cells",
})
_CELL_KEYS = frozenset({
    "opponent_id", "seed", "seat",
    "incumbent_own", "incumbent_rival",
    "champion_own", "champion_rival",
    "candidate_own", "candidate_rival",
})


class ChampionError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ChampionError(f"duplicate JSON object key: {key}")
        out[key] = value
    return out


def _reject_constant(token: str) -> None:
    raise ChampionError(f"non-finite JSON constant is forbidden: {token}")


def _loads(text: str, source: str = "<memory>") -> Any:
    try:
        return json.loads(text, object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise ChampionError(f"{source}: invalid JSON: {exc.msg}") from exc


def _v5c(value: Any, field: str) -> str:
    if type(value) is not str or _V5C.fullmatch(value) is None:
        raise ChampionError(f"{field} must be v5c:<64 lowercase hex>")
    return value


def _hex64(value: Any, field: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise ChampionError(f"{field} must be 64 lowercase hex characters")
    return value


def _text(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or not value.strip():
        raise ChampionError(f"{field} must be a non-empty string")
    return value


def _int(value: Any, field: str, lo: int = 0, hi: int = MAX_INT) -> int:
    if type(value) is not int or not lo <= value <= hi:
        raise ChampionError(f"{field} must be a plain int in [{lo}, {hi}]")
    return value


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    if type(report) is not dict:
        raise ChampionError("champion report must be an object")
    if set(report) != _REPORT_KEYS:
        missing = sorted(_REPORT_KEYS - set(report))
        extra = sorted(set(report) - _REPORT_KEYS)
        raise ChampionError(f"champion report keys mismatch; missing={missing!r} extra={extra!r}")
    if report["schema"] != SCHEMA:
        raise ChampionError(f"champion report schema must be {SCHEMA}")

    incumbent_id = _v5c(report["incumbent_id"], "incumbent_id")
    candidate_id = _v5c(report["candidate_id"], "candidate_id")
    if incumbent_id == candidate_id:
        raise ChampionError("incumbent_id and candidate_id must differ")
    engine_id = _text(report["engine_id"], "engine_id")
    opponent_pack_id = _text(report["opponent_pack_id"], "opponent_pack_id", nullable=True)

    incumbent_archive = _hex64(report["incumbent_archive_sha256"], "incumbent_archive_sha256")
    champion_archive = _hex64(report["champion_archive_sha256"], "champion_archive_sha256")
    candidate_archive = _hex64(report["candidate_archive_sha256"], "candidate_archive_sha256")
    if champion_archive != V31_ARCHIVE_SHA256:
        raise ChampionError("champion archive is not exact submitted V3.1")
    if len({incumbent_archive, champion_archive, candidate_archive}) != 3:
        raise ChampionError("incumbent, champion, and candidate archives must be distinct")

    cells = report["cells"]
    if type(cells) is not list:
        raise ChampionError("cells must be a list")
    if len(cells) < MIN_OPPONENTS * MIN_SEEDS * 2:
        raise ChampionError("champion panel is too small")

    keys: list[tuple[str, int, int]] = []
    seats: dict[tuple[str, int], set[int]] = {}
    seeds_by_opp: dict[str, set[int]] = {}
    stratum: dict[tuple[str, int], dict[str, int]] = {}
    totals = {name: 0 for name in (
        "incumbent_own", "champion_own", "candidate_own",
        "incumbent_margin", "champion_margin", "candidate_margin",
    )}
    new_losses_vs_incumbent = 0
    new_losses_vs_champion = 0
    own_delta_vs_incumbent: list[int] = []
    own_delta_vs_champion: list[int] = []

    for idx, cell in enumerate(cells):
        field = f"cells[{idx}]"
        if type(cell) is not dict or set(cell) != _CELL_KEYS:
            raise ChampionError(f"{field} must have exact raw score keys")
        opponent = _text(cell["opponent_id"], f"{field}.opponent_id")
        assert isinstance(opponent, str)
        seed = _int(cell["seed"], f"{field}.seed")
        seat = _int(cell["seat"], f"{field}.seat", 0, 1)
        key = (opponent, seed, seat)
        keys.append(key)
        seats.setdefault((opponent, seed), set()).add(seat)
        seeds_by_opp.setdefault(opponent, set()).add(seed)

        vals = {k: _int(cell[k], f"{field}.{k}") for k in _CELL_KEYS if k.endswith("_own") or k.endswith("_rival")}
        im = vals["incumbent_own"] - vals["incumbent_rival"]
        hm = vals["champion_own"] - vals["champion_rival"]
        cm = vals["candidate_own"] - vals["candidate_rival"]
        totals["incumbent_own"] += vals["incumbent_own"]
        totals["champion_own"] += vals["champion_own"]
        totals["candidate_own"] += vals["candidate_own"]
        totals["incumbent_margin"] += im
        totals["champion_margin"] += hm
        totals["candidate_margin"] += cm
        own_delta_vs_incumbent.append(vals["candidate_own"] - vals["incumbent_own"])
        own_delta_vs_champion.append(vals["candidate_own"] - vals["champion_own"])
        if im >= 0 and cm < 0:
            new_losses_vs_incumbent += 1
        if hm >= 0 and cm < 0:
            new_losses_vs_champion += 1
        bucket = stratum.setdefault((opponent, seat), {"n": 0, "incumbent_own": 0, "champion_own": 0, "candidate_own": 0})
        bucket["n"] += 1
        bucket["incumbent_own"] += vals["incumbent_own"]
        bucket["champion_own"] += vals["champion_own"]
        bucket["candidate_own"] += vals["candidate_own"]

    if len(keys) != len(set(keys)):
        raise ChampionError("opponent/seed/seat cells must be unique")
    if keys != sorted(keys):
        raise ChampionError("cells must be sorted by opponent_id, seed, seat")
    opponents = sorted(seeds_by_opp)
    if len(opponents) < MIN_OPPONENTS:
        raise ChampionError(f"panel requires at least {MIN_OPPONENTS} opponents")
    reference = seeds_by_opp[opponents[0]]
    if len(reference) < MIN_SEEDS:
        raise ChampionError(f"panel requires at least {MIN_SEEDS} seeds per opponent")
    if any(seeds_by_opp[opp] != reference for opp in opponents[1:]):
        raise ChampionError("all opponents must cover the identical seed set")
    incomplete = [(opp, seed) for opp in opponents for seed in sorted(reference) if seats.get((opp, seed)) != {0, 1}]
    if incomplete:
        raise ChampionError(f"every opponent/seed requires both seats; incomplete={incomplete!r}")
    expected = len(opponents) * len(reference) * 2
    if len(cells) != expected:
        raise ChampionError("panel topology is not balanced")

    own_inc = totals["candidate_own"] - totals["incumbent_own"]
    own_v31 = totals["candidate_own"] - totals["champion_own"]
    margin_inc = totals["candidate_margin"] - totals["incumbent_margin"]
    margin_v31 = totals["candidate_margin"] - totals["champion_margin"]
    if own_inc < 0:
        raise ChampionError(f"candidate regresses incumbent own score: sum_delta={own_inc}")
    if own_v31 <= 0:
        raise ChampionError(f"candidate does not strictly beat V3.1 own score: sum_delta={own_v31}")
    if margin_inc < 0:
        raise ChampionError(f"candidate regresses incumbent margin: sum_delta={margin_inc}")
    if margin_v31 < 0:
        raise ChampionError(f"candidate regresses V3.1 margin: sum_delta={margin_v31}")
    if new_losses_vs_incumbent or new_losses_vs_champion:
        raise ChampionError(
            f"candidate creates new losses: incumbent={new_losses_vs_incumbent} champion={new_losses_vs_champion}"
        )

    strata = []
    for (opponent, seat), bucket in sorted(stratum.items()):
        d_inc = bucket["candidate_own"] - bucket["incumbent_own"]
        d_v31 = bucket["candidate_own"] - bucket["champion_own"]
        if d_inc < 0 or d_v31 < 0:
            raise ChampionError(
                f"negative own-score stratum opponent={opponent!r} seat={seat} incumbent_delta={d_inc} v31_delta={d_v31}"
            )
        strata.append({
            "opponent_id": opponent,
            "seat": seat,
            "cell_count": bucket["n"],
            "own_delta_vs_incumbent": d_inc,
            "own_delta_vs_v31": d_v31,
        })

    n = len(cells)
    mean_own_v31 = own_v31 / n
    mean_own_inc = own_inc / n
    mean_margin_v31 = margin_v31 / n
    mean_margin_inc = margin_inc / n
    if not all(math.isfinite(v) for v in (mean_own_v31, mean_own_inc, mean_margin_v31, mean_margin_inc)):
        raise ChampionError("non-finite aggregate")

    return {
        "schema": RECEIPT_SCHEMA,
        "classification": "PASS",
        "champion_ready": True,
        "incumbent_id": incumbent_id,
        "candidate_id": candidate_id,
        "engine_id": engine_id,
        "opponent_pack_id": opponent_pack_id,
        "incumbent_archive_sha256": incumbent_archive,
        "champion_archive_sha256": champion_archive,
        "candidate_archive_sha256": candidate_archive,
        "opponent_ids": opponents,
        "opponent_count": len(opponents),
        "seed_count": len(reference),
        "cell_count": n,
        "own_sum_delta_vs_incumbent": own_inc,
        "own_mean_delta_vs_incumbent": mean_own_inc,
        "own_sum_delta_vs_v31": own_v31,
        "own_mean_delta_vs_v31": mean_own_v31,
        "margin_sum_delta_vs_incumbent": margin_inc,
        "margin_mean_delta_vs_incumbent": mean_margin_inc,
        "margin_sum_delta_vs_v31": margin_v31,
        "margin_mean_delta_vs_v31": mean_margin_v31,
        "positive_own_cells_vs_v31": sum(v > 0 for v in own_delta_vs_champion),
        "negative_own_cells_vs_v31": sum(v < 0 for v in own_delta_vs_champion),
        "positive_own_cells_vs_incumbent": sum(v > 0 for v in own_delta_vs_incumbent),
        "negative_own_cells_vs_incumbent": sum(v < 0 for v in own_delta_vs_incumbent),
        "strata": strata,
        "panel_sha256": hashlib.sha256(_canon(cells)).hexdigest(),
    }


def _load(path: Path) -> Mapping[str, Any]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ChampionError(f"cannot read UTF-8 report: {path}") from exc
    value = _loads(text, str(path))
    if type(value) is not dict:
        raise ChampionError("champion report must be an object")
    return value


def _emit(receipt: Mapping[str, Any], output: Path | None) -> None:
    payload = _canon(receipt) + b"\n"
    if output is None:
        sys.stdout.buffer.write(payload)
        return
    tmp = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, output)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        _emit(validate_report(_load(args.report)), args.output)
    except (ChampionError, OSError, TypeError, ValueError) as exc:
        print(f"champion_gate: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
