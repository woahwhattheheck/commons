#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Static authored-action census for the V3.1 R04 fertilizer/JIT lane.

This deliberately answers only what is encoded in the thirteen published R04
action tapes.  It does not claim that an authored action will execute, that a
FERTILIZE targets a particular crop, or that an idle slot is economically free.
Those questions require official-engine replay from an exact materialized V3.1
candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
CLOUD_ROOT = HERE.parents[1]
TAPES_PATH = CLOUD_ROOT / "candidates" / "v3" / "overlay" / "r01_tapes.py"
EXPECTED_ROUTES = 13
EXPECTED_STEPS = 719
MIN_IDLE_STREAK = 6
TRACKED_UNIT_OPS = ("FERTILIZE", "WATER", "COLLECT_FERTILIZER", "PASS")


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location("titan_v31_r01_tapes_for_b5_audit", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import tape module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_current_tapes(path: Path = TAPES_PATH) -> list[list[dict[str, Any]]]:
    """Decode the exact committed R01 tape carrier without mutating its objects."""
    if not path.is_file():
        raise FileNotFoundError(path)
    module = _load_module(path)
    loader = getattr(module, "load_tapes", None)
    if not callable(loader):
        raise RuntimeError(f"{path} does not expose load_tapes()")
    tapes = loader()
    if not isinstance(tapes, list):
        raise TypeError("load_tapes() must return a list")
    return tapes


def _op(action: Any) -> str:
    if not isinstance(action, list) or not action:
        return "PASS"
    value = action[0]
    return value if isinstance(value, str) and value else "MALFORMED"


def _units(row: dict[str, Any]) -> list[Any]:
    farmer = row.get("farmer", ["PASS"])
    hands = row.get("hands", [])
    if not isinstance(hands, list):
        hands = []
    return [farmer, *hands]


def _close_streak(
    out: list[dict[str, int]], worker: int, start: int, stop_exclusive: int
) -> None:
    length = stop_exclusive - start
    if length >= MIN_IDLE_STREAK:
        out.append(
            {
                "worker": worker,
                "start_step": start,
                "end_step": stop_exclusive - 1,
                "length": length,
                "start_day": start // 24,
                "end_day": (stop_exclusive - 1) // 24,
            }
        )


def audit_tapes(tapes: Iterable[list[dict[str, Any]]]) -> dict[str, Any]:
    """Return a deterministic census of authored service/input/idle actions.

    PASS streaks count only workers whose action slot exists in the tape row;
    absent future hand slots are never credited as idle capacity.  Market counts
    use the first ten rows, matching the canonical maxMarketOrdersPerTurn gate.
    """
    routes = list(tapes)
    report_routes: list[dict[str, Any]] = []
    global_units: Counter[str] = Counter()
    global_market: Counter[str] = Counter()
    total_steps = 0

    for route_index, tape in enumerate(routes):
        if not isinstance(tape, list):
            raise TypeError(f"route {route_index} is not a list")
        unit_counts: Counter[str] = Counter()
        market_counts: Counter[str] = Counter()
        daily: dict[int, Counter[str]] = defaultdict(Counter)
        fertilizer_events: list[dict[str, Any]] = []
        idle_streaks: list[dict[str, int]] = []
        open_idle: dict[int, int] = {}
        max_workers = 0

        for step, row in enumerate(tape):
            if not isinstance(row, dict):
                raise TypeError(f"route {route_index} step {step} is not an object")
            total_steps += 1
            units = _units(row)
            present = set(range(len(units)))
            max_workers = max(max_workers, len(units))

            for worker in sorted(set(open_idle) - present):
                _close_streak(idle_streaks, worker, open_idle.pop(worker), step)

            for worker, action in enumerate(units):
                op = _op(action)
                unit_counts[op] += 1
                global_units[op] += 1
                if op in TRACKED_UNIT_OPS:
                    daily[step // 24][op] += 1
                if op == "PASS":
                    open_idle.setdefault(worker, step)
                else:
                    if worker in open_idle:
                        _close_streak(idle_streaks, worker, open_idle.pop(worker), step)
                if op in ("FERTILIZE", "COLLECT_FERTILIZER"):
                    fertilizer_events.append(
                        {
                            "step": step,
                            "day": step // 24,
                            "hour": step % 24,
                            "worker": worker,
                            "op": op,
                            "action": list(action) if isinstance(action, list) else action,
                        }
                    )

            market = row.get("market", [])
            if not isinstance(market, list):
                market = []
            for slot, order in enumerate(market[:10]):
                if not isinstance(order, list) or len(order) < 2:
                    continue
                op, item = order[0], order[1]
                if item != "FERTILIZER" or op not in ("BUY_PRODUCT", "SELL"):
                    continue
                key = f"{op}:FERTILIZER"
                market_counts[key] += 1
                global_market[key] += 1
                fertilizer_events.append(
                    {
                        "step": step,
                        "day": step // 24,
                        "hour": step % 24,
                        "market_slot": slot,
                        "op": op,
                        "item": item,
                        "quantity": order[2] if len(order) >= 3 else None,
                    }
                )

        for worker, start in sorted(open_idle.items()):
            _close_streak(idle_streaks, worker, start, len(tape))

        tracked_daily = {
            str(day): {op: counts.get(op, 0) for op in TRACKED_UNIT_OPS if counts.get(op, 0)}
            for day, counts in sorted(daily.items())
            if any(counts.get(op, 0) for op in TRACKED_UNIT_OPS)
        }
        report_routes.append(
            {
                "route": route_index,
                "steps": len(tape),
                "max_authored_workers": max_workers,
                "unit_counts": dict(sorted(unit_counts.items())),
                "fertilizer_market_counts": dict(sorted(market_counts.items())),
                "tracked_by_day": tracked_daily,
                "fertilizer_events": fertilizer_events,
                "idle_streaks_ge_6": idle_streaks,
            }
        )

    return {
        "schema": 1,
        "scope": "static authored R04 tape census; not execution, legality, tile-target, or value evidence",
        "route_count": len(routes),
        "total_steps": total_steps,
        "global_unit_counts": dict(sorted(global_units.items())),
        "global_fertilizer_market_counts": dict(sorted(global_market.items())),
        "routes": report_routes,
    }


def audit_current(path: Path = TAPES_PATH) -> dict[str, Any]:
    tapes = load_current_tapes(path)
    if len(tapes) != EXPECTED_ROUTES:
        raise RuntimeError(f"expected {EXPECTED_ROUTES} routes, got {len(tapes)}")
    bad = [i for i, tape in enumerate(tapes) if len(tape) != EXPECTED_STEPS]
    if bad:
        raise RuntimeError(f"routes with non-{EXPECTED_STEPS} length: {bad}")
    report = audit_tapes(tapes)
    raw = path.read_bytes()
    report["source"] = {
        "path": str(path.relative_to(CLOUD_ROOT)),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    canonical = json.dumps(report["routes"], sort_keys=True, separators=(",", ":")).encode()
    report["route_census_sha256"] = hashlib.sha256(canonical).hexdigest()
    return report


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    counts = report["global_unit_counts"]
    idle_windows = sum(len(route["idle_streaks_ge_6"]) for route in report["routes"])
    return {
        "routes": report["route_count"],
        "steps": report["total_steps"],
        "fertilize": counts.get("FERTILIZE", 0),
        "water": counts.get("WATER", 0),
        "collect_fertilizer": counts.get("COLLECT_FERTILIZER", 0),
        "pass": counts.get("PASS", 0),
        "fertilizer_buys": report["global_fertilizer_market_counts"].get("BUY_PRODUCT:FERTILIZER", 0),
        "fertilizer_sells": report["global_fertilizer_market_counts"].get("SELL:FERTILIZER", 0),
        "idle_streaks_ge_6": idle_windows,
        "route_census_sha256": report.get("route_census_sha256"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write full JSON receipt")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args(argv)
    report = audit_current()
    summary = _summary(report)
    print("B5_R04_CENSUS " + json.dumps(summary, sort_keys=True))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif not args.summary_only:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
