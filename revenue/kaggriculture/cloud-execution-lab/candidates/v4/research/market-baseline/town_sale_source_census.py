#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-bound current-Arlene census for deterministic TOWNSELL windows.

This module does *not* retime an action.  It consumes the merged TOWNSELL theorem
and asks a narrower prerequisite question: does the current authored Arlene route
bank contain executable-prefix SELL rows immediately before a town-center drain
whose one-callback deferral has a structurally quiet landing slot?

Only guaranteed town-center demand is counted here (unlocked shops are passed as
an empty set).  Dynamic Arlene guards, actual shed stock, rival flow, prices and
cash remain current-native execution gates, so a positive source census is never
activation authority.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[3]
ARLENE = LAB / "reference" / "next-panel" / "vendor" / "arlene.py"
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"
TOWNSELL = HERE / "town_sale_deferral.py"
TOWN_TIMING = HERE / "town_wheat_timing.py"

EXPECTED_ARLENE_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"
EXPECTED_ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
EXPECTED_TOWNSELL_BLOB = "a795cc75dfcaa097e1b081114bbc09fb94e16f86"
EXPECTED_TOWN_TIMING_BLOB = "abdbdc74ddc2be60cc46ae53b069998fdb3bff3b"
FINAL_EXECUTABLE_STEP = 718
BLOCKING_NEXT_UNIT_OPS = frozenset({"DROP", "PLACE"})


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def require_source_identity() -> dict[str, str]:
    observed = {
        "arlene": git_blob(ARLENE),
        "engine": git_blob(ENGINE),
        "townsell": git_blob(TOWNSELL),
        "town_timing": git_blob(TOWN_TIMING),
    }
    expected = {
        "arlene": EXPECTED_ARLENE_BLOB,
        "engine": EXPECTED_ENGINE_BLOB,
        "townsell": EXPECTED_TOWNSELL_BLOB,
        "town_timing": EXPECTED_TOWN_TIMING_BLOB,
    }
    bad = [name for name in expected if observed[name] != expected[name]]
    if bad:
        detail = ", ".join(
            f"{name}: expected {expected[name]}, got {observed[name]}" for name in bad
        )
        raise RuntimeError(f"TOWNSELL source identity drift: {detail}")
    return observed


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row_op(row: Any) -> str | None:
    return row[0] if isinstance(row, list) and row and isinstance(row[0], str) else None


def _positive_quantity(row: Any) -> int | None:
    if not isinstance(row, list) or len(row) < 3:
        return None
    qty = row[2]
    if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
        return None
    return qty


def _market(action: Any) -> list[Any] | None:
    if not isinstance(action, dict):
        return None
    raw = action.get("market", [])
    return raw if isinstance(raw, list) else None


def _unit_ops(action: Any) -> list[str]:
    if not isinstance(action, dict):
        return ["<MALFORMED_ACTION>"]
    rows: list[Any] = [action.get("farmer", ["PASS"])]
    hands = action.get("hands", [])
    if not isinstance(hands, list):
        return ["<MALFORMED_HANDS>"]
    rows.extend(hands)
    return [op for op in (_row_op(row) for row in rows) if op is not None]


def structural_blockers(route: list[Any], step: int, item: str, *, max_orders: int) -> list[str]:
    """Fail-closed source-only blockers for moving a SELL from t to t+1.

    These guards prove only a quiet authored landing shape.  They intentionally do
    not model runtime stock, rival actions or prices.
    """
    blockers: list[str] = []
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        return ["invalid_step"]
    if step >= FINAL_EXECUTABLE_STEP or step + 1 >= len(route):
        return ["terminal_horizon"]
    next_action = route[step + 1]
    next_market = _market(next_action)
    if next_market is None:
        return ["next_market_not_list"]
    prefix = next_market[:max_orders]
    if len(next_market) >= max_orders:
        blockers.append("next_market_no_append_slot")
    for row in prefix:
        op = _row_op(row)
        if op is None:
            if row:
                blockers.append("next_market_malformed_row")
            continue
        if op != "SELL":
            blockers.append("next_market_cash_or_order_dependency")
        elif len(row) > 1 and row[1] == item:
            blockers.append("next_market_same_item_sell")
    if any(op in BLOCKING_NEXT_UNIT_OPS for op in _unit_ops(next_action)):
        blockers.append("next_unit_can_write_shed")
    return sorted(set(blockers))


def census_route(route_id: str, route: Any, engine, timing, *, max_orders: int) -> dict[str, Any]:
    if not isinstance(route, list):
        raise RuntimeError(f"route {route_id}: expected list")
    guaranteed: list[dict[str, Any]] = []
    safe_shape: list[dict[str, Any]] = []
    for step, action in enumerate(route):
        market = _market(action)
        if market is None:
            raise RuntimeError(f"route {route_id} step {step}: market is not list")
        for row_index, row in enumerate(market[:max_orders]):
            if _row_op(row) != "SELL" or len(row) < 2 or not isinstance(row[1], str):
                continue
            item = row[1]
            qty = _positive_quantity(row)
            if qty is None or item not in engine.PRODUCTS:
                continue
            # Empty shops makes this a lower bound: only the deterministic town
            # center can contribute demand.  Shop RNG is therefore never guessed.
            demand = timing.town_demand_units(engine, step, [], item=item)
            if demand <= 0:
                continue
            blockers = structural_blockers(route, step, item, max_orders=max_orders)
            record = {
                "route": route_id,
                "step": step,
                "row_index": row_index,
                "item": item,
                "authored_quantity": qty,
                "guaranteed_town_center_drain": demand,
                "blockers": blockers,
                "source_safe_shape": not blockers,
            }
            guaranteed.append(record)
            if not blockers:
                safe_shape.append(record)
    return {
        "route": route_id,
        "turns": len(route),
        "guaranteed_windows": guaranteed,
        "source_safe_windows": safe_shape,
    }


def census() -> dict[str, Any]:
    identity = require_source_identity()
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    arlene = load_module(ARLENE, "_townsell_current_arlene")
    baseline = load_module(HERE / "engine_bound_baseline.py", "_townsell_engine_bound")
    timing = load_module(TOWN_TIMING, "_townsell_timing")
    engine = baseline.load_engine(ENGINE)
    if getattr(arlene, "MAX_ORDERS", None) != 10:
        raise RuntimeError(f"unexpected Arlene MAX_ORDERS: {getattr(arlene, 'MAX_ORDERS', None)!r}")
    routes = arlene.routes()
    if not isinstance(routes, dict) or not routes:
        raise RuntimeError("current Arlene routes missing")

    rows = [
        census_route(route_id, route, engine, timing, max_orders=arlene.MAX_ORDERS)
        for route_id, route in sorted(routes.items())
    ]
    guaranteed = [w for row in rows for w in row["guaranteed_windows"]]
    safe = [w for row in rows for w in row["source_safe_windows"]]
    by_item: dict[str, int] = {}
    for row in safe:
        by_item[row["item"]] = by_item.get(row["item"], 0) + 1
    status = "SOURCE_SAFE_SHAPE_REQUIRES_CURRENT_NATIVE" if safe else "COLD_SOURCE_NO_SAFE_SHAPE"
    return {
        "schema": "titan-v4-townsell-source-census/v1",
        "status": status,
        "source_identity": identity,
        "current_authority": {
            "arlene_main": getattr(arlene, "MAIN", None),
            "route_ids": sorted(routes),
            "route_count": len(routes),
            "max_market_orders": arlene.MAX_ORDERS,
            "final_executable_step": FINAL_EXECUTABLE_STEP,
        },
        "counts": {
            "guaranteed_town_center_sell_windows": len(guaranteed),
            "source_safe_windows": len(safe),
            "source_safe_by_item": dict(sorted(by_item.items())),
        },
        "source_safe_windows": safe,
        "routes": rows,
        "gate": {
            "meaning": (
                "Positive rows prove only an authored executable-prefix SELL and a quiet source-shaped "
                "landing slot around guaranteed town-center demand."
            ),
            "required_next": [
                "authenticate one current-native postimage",
                "observe the SELL after Arlene clamp_sells/dead_stock/terminal settlement",
                "prove sufficient shed custody through the deferred callback",
                "prove no cash deadline or capacity loss",
                "exclude or measure rival same-item flow",
                "run paired both-seat economics before any composition/runtime proposal",
            ],
            "forbidden_inference": "source-safe is not a retiming or promotion authorization",
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = census()
    if args.json:
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    else:
        print(report["status"])
        print(json.dumps(report["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
