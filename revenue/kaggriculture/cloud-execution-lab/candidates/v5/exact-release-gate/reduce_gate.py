#!/usr/bin/env python3
"""Deterministic TITAN V5 exact-release gate reducer.

Consumes a strict, normalized evidence bundle. It never runs games, mutates
release pointers, or submits to Kaggle. Its job is to make identity/cell
coverage/statistical gate facts reproducible and fail closed on ambiguity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

SCHEMA = "titan.v5.exact-release-gate.v1"
REPORT_SCHEMA = "titan.v5.exact-release-gate-report.v1"
CANDIDATE_SHA256 = "8b4b074012fe3bd731c218a4956f85ce8dadd74d5afe81a3e04c2795a2a533ee"
CONTROL_SHA256 = "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"
ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
REQUIRED_LANES = frozenset({"F24", "F25", "F26", "F27", "F28", "F29"})
EXPECTED_LANE_CELL_COUNTS = {"F24": 16, "F25": 16, "F26": 64, "F27": 62, "F28": 60, "F29": 60}
_SUCCESS = frozenset({"OK", "COMPLETE", "SUCCESS"})
_FAILURE_TOKENS = ("DQ", "DISQUAL", "TIMEOUT", "FALLBACK", "PACKAGE_MISMATCH", "MISMATCH")
_SHA256 = set("0123456789abcdef")


class GateError(ValueError):
    pass


def _builtin_str(v: Any, name: str) -> str:
    if type(v) is not str or not v:
        raise GateError(f"{name} must be a nonempty built-in string")
    return v


def _builtin_int(v: Any, name: str) -> int:
    if type(v) is not int:
        raise GateError(f"{name} must be a built-in integer")
    return v


def _sha(v: Any, name: str) -> str:
    s = _builtin_str(v, name)
    if len(s) != 64 or any(ch not in _SHA256 for ch in s):
        raise GateError(f"{name} must be lowercase sha256 hex")
    return s


def _status(v: Any, name: str) -> str:
    return _builtin_str(v, name).upper()


def _percentile_nearest_rank(values: list[int], pct: float) -> int:
    if not values:
        raise GateError("cannot reduce an empty value set")
    if not 0 < pct <= 1:
        raise GateError("percentile must be in (0,1]")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(pct * len(ordered)) - 1)]


def _canonical_json(payload: Any) -> str:
    try:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise GateError("bundle/report must be canonical JSON-compatible data") from exc


@dataclass(frozen=True)
class Outcome:
    status: str
    own: int
    rival: int
    callback_max_ms: int
    fallback_count: int

    @classmethod
    def parse(cls, raw: Any, prefix: str) -> "Outcome":
        if type(raw) is not dict:
            raise GateError(f"{prefix} must be an object")
        expected = {"status", "own_score", "rival_score", "callback_max_ms", "fallback_count"}
        if set(raw) != expected:
            raise GateError(f"{prefix} keys must equal {sorted(expected)}")
        status = _status(raw["status"], f"{prefix}.status")
        own = _builtin_int(raw["own_score"], f"{prefix}.own_score")
        rival = _builtin_int(raw["rival_score"], f"{prefix}.rival_score")
        callback = _builtin_int(raw["callback_max_ms"], f"{prefix}.callback_max_ms")
        fallbacks = _builtin_int(raw["fallback_count"], f"{prefix}.fallback_count")
        if callback < 0 or fallbacks < 0:
            raise GateError(f"{prefix} timing/fallback values must be nonnegative")
        return cls(status, own, rival, callback, fallbacks)

    @property
    def margin(self) -> int:
        return self.own - self.rival

    @property
    def clean(self) -> bool:
        if self.status not in _SUCCESS:
            return False
        if any(token in self.status for token in _FAILURE_TOKENS):
            return False
        return self.fallback_count == 0


@dataclass(frozen=True)
class Cell:
    cell_id: str
    lane: str
    fixture_id: str
    opponent: str
    family: str
    seat: int
    candidate: Outcome
    control: Outcome

    @classmethod
    def parse(cls, raw: Any) -> "Cell":
        if type(raw) is not dict:
            raise GateError("each cell must be an object")
        expected = {"cell_id", "lane", "fixture_id", "opponent", "family", "seat", "candidate", "control"}
        if set(raw) != expected:
            raise GateError(f"cell keys must equal {sorted(expected)}")
        lane = _builtin_str(raw["lane"], "cell.lane")
        if lane not in REQUIRED_LANES:
            raise GateError(f"unsupported lane {lane}")
        seat = _builtin_int(raw["seat"], "cell.seat")
        if seat not in (0, 1):
            raise GateError("cell.seat must be 0 or 1")
        return cls(
            cell_id=_builtin_str(raw["cell_id"], "cell.cell_id"),
            lane=lane,
            fixture_id=_builtin_str(raw["fixture_id"], "cell.fixture_id"),
            opponent=_builtin_str(raw["opponent"], "cell.opponent"),
            family=_builtin_str(raw["family"], "cell.family"),
            seat=seat,
            candidate=Outcome.parse(raw["candidate"], "cell.candidate"),
            control=Outcome.parse(raw["control"], "cell.control"),
        )

    @property
    def delta(self) -> int:
        return self.candidate.margin - self.control.margin

    @property
    def candidate_result(self) -> str:
        return "W" if self.candidate.margin > 0 else "L" if self.candidate.margin < 0 else "T"

    @property
    def control_result(self) -> str:
        return "W" if self.control.margin > 0 else "L" if self.control.margin < 0 else "T"


def _summarize(cells: Iterable[Cell]) -> dict[str, Any]:
    rows = list(cells)
    ds = [c.delta for c in rows]
    wins = sum(c.candidate_result == "W" for c in rows)
    losses = sum(c.candidate_result == "L" for c in rows)
    ties = len(rows) - wins - losses
    control_wins = sum(c.control_result == "W" for c in rows)
    control_losses = sum(c.control_result == "L" for c in rows)
    control_ties = len(rows) - control_wins - control_losses
    return {
        "n": len(rows),
        "mean_delta": mean(ds),
        "median_delta": median(ds),
        "p10_delta": _percentile_nearest_rank(ds, 0.10),
        "worst_delta": min(ds),
        "positive": sum(d > 0 for d in ds),
        "zero": sum(d == 0 for d in ds),
        "negative": sum(d < 0 for d in ds),
        "candidate_wlt": {"W": wins, "L": losses, "T": ties},
        "control_wlt": {"W": control_wins, "L": control_losses, "T": control_ties},
        "loss_to_win": sum(c.control_result == "L" and c.candidate_result == "W" for c in rows),
        "win_to_loss": sum(c.control_result == "W" and c.candidate_result == "L" for c in rows),
        "callback_max_ms": max(max(c.candidate.callback_max_ms, c.control.callback_max_ms) for c in rows),
    }


def _groups(cells: list[Cell], key):
    buckets = defaultdict(list)
    for c in cells:
        buckets[key(c)].append(c)
    return sorted(buckets.items(), key=lambda kv: str(kv[0]))


def evaluate(bundle: Any) -> dict[str, Any]:
    if type(bundle) is not dict:
        raise GateError("bundle must be an object")
    expected = {"schema_version", "candidate_sha256", "control_sha256", "engine_sha256", "lane_receipts", "cells"}
    if set(bundle) != expected:
        raise GateError(f"bundle keys must equal {sorted(expected)}")
    if bundle["schema_version"] != SCHEMA:
        raise GateError("unsupported schema_version")
    if _sha(bundle["candidate_sha256"], "candidate_sha256") != CANDIDATE_SHA256:
        raise GateError("candidate identity mismatch")
    if _sha(bundle["control_sha256"], "control_sha256") != CONTROL_SHA256:
        raise GateError("V3.1 control identity mismatch")
    if _sha(bundle["engine_sha256"], "engine_sha256") != ENGINE_SHA256:
        raise GateError("engine identity mismatch")

    receipts = bundle["lane_receipts"]
    if type(receipts) is not dict or set(receipts) != REQUIRED_LANES:
        raise GateError("lane_receipts must name exactly F24-F29")
    normalized_receipts = {}
    receipt_keys = {"raw_artifact", "raw_sha256", "corpus_id", "corpus_sha256"}
    for lane, raw in receipts.items():
        if type(raw) is not dict or set(raw) != receipt_keys:
            raise GateError(f"lane_receipts.{lane} keys must equal {sorted(receipt_keys)}")
        normalized_receipts[lane] = {
            "raw_artifact": _builtin_str(raw["raw_artifact"], f"lane_receipts.{lane}.raw_artifact"),
            "raw_sha256": _sha(raw["raw_sha256"], f"lane_receipts.{lane}.raw_sha256"),
            "corpus_id": _builtin_str(raw["corpus_id"], f"lane_receipts.{lane}.corpus_id"),
            "corpus_sha256": _sha(raw["corpus_sha256"], f"lane_receipts.{lane}.corpus_sha256"),
        }

    raw_cells = bundle["cells"]
    if type(raw_cells) is not list or not raw_cells:
        raise GateError("cells must be a nonempty array")
    cells = [Cell.parse(raw) for raw in raw_cells]

    ids = [c.cell_id for c in cells]
    if len(ids) != len(set(ids)):
        raise GateError("duplicate cell_id")
    semantic_keys = [(c.lane, c.fixture_id, c.opponent, c.seat) for c in cells]
    if len(semantic_keys) != len(set(semantic_keys)):
        raise GateError("duplicate semantic cell")

    observed = {lane: 0 for lane in REQUIRED_LANES}
    for c in cells:
        observed[c.lane] += 1
    if observed != EXPECTED_LANE_CELL_COUNTS:
        raise GateError(f"lane coverage mismatch: observed={observed}, required={EXPECTED_LANE_CELL_COUNTS}")

    dirty = [c.cell_id for c in cells if not c.candidate.clean or not c.control.clean]
    overall = _summarize(cells)
    by_family = {family: _summarize(group) for family, group in _groups(cells, lambda c: c.family)}
    by_seat = {str(seat): _summarize(group) for seat, group in _groups(cells, lambda c: c.seat)}
    by_lane = {lane: _summarize(group) for lane, group in _groups(cells, lambda c: c.lane)}

    machine_failures = []
    if dirty:
        machine_failures.append("nonclean_status_or_fallback")
    if overall["mean_delta"] <= 0:
        machine_failures.append("global_mean_not_positive")
    if overall["median_delta"] <= 0:
        machine_failures.append("global_median_not_positive")
    if overall["loss_to_win"] < overall["win_to_loss"]:
        machine_failures.append("loss_to_win_below_win_to_loss")

    failure_counts = {
        "non_success_status": sum(c.candidate.status not in _SUCCESS or c.control.status not in _SUCCESS for c in cells),
        "dq_or_disqualification": sum("DQ" in c.candidate.status or "DISQUAL" in c.candidate.status or "DQ" in c.control.status or "DISQUAL" in c.control.status for c in cells),
        "timeout": sum("TIMEOUT" in c.candidate.status or "TIMEOUT" in c.control.status for c in cells),
        "fallback": sum(c.candidate.fallback_count + c.control.fallback_count for c in cells),
        "package_or_abi_mismatch": sum("MISMATCH" in c.candidate.status or "MISMATCH" in c.control.status or "ABI" in c.candidate.status or "ABI" in c.control.status for c in cells),
    }
    worst_20 = [
        {"cell_id": c.cell_id, "lane": c.lane, "fixture_id": c.fixture_id, "opponent": c.opponent, "family": c.family, "seat": c.seat, "delta": c.delta}
        for c in sorted(cells, key=lambda c: (c.delta, c.cell_id))[:20]
    ]

    report = {
        "schema_version": REPORT_SCHEMA,
        "candidate_sha256": CANDIDATE_SHA256,
        "control_sha256": CONTROL_SHA256,
        "engine_sha256": ENGINE_SHA256,
        "cell_count": len(cells),
        "lane_cell_counts": observed,
        "lane_receipts": normalized_receipts,
        "dirty_cells": dirty,
        "failure_counts": failure_counts,
        "worst_20": worst_20,
        "overall": overall,
        "by_family": by_family,
        "by_seat": by_seat,
        "by_lane": by_lane,
        "machine_failures": machine_failures,
        "machine_status": "PASS" if not machine_failures else "HOLD",
        "root_review_required": {"family_median_adequate_n": True, "lower_tail_materially_unlike_v4": True, "catastrophic_regressions_explained": True},
        "release_status": "AWAIT_ROOT_REVIEW" if not machine_failures else "HOLD",
    }
    report["report_sha256"] = hashlib.sha256(_canonical_json(report).encode("utf-8")).hexdigest()
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundle", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        report = evaluate(bundle)
    except (OSError, json.JSONDecodeError, GateError) as exc:
        p.error(str(exc))
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
