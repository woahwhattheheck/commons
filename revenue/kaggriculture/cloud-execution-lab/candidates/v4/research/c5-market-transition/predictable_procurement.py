#!/usr/bin/env python3
"""Fail-closed atlas of publicly predictable Arlene BUY_PRODUCT pulses.

This is research/census support for the existing C5 market-transition authority.
It does not observe a rival's current private action and it does not mutate policy.

A pulse is policy-safe evidence only when all of the following hold:
* the exact vendored Arlene source is authenticated;
* the same positive BUY_PRODUCT WHEAT/FERTILIZER row appears in every route;
* the row is inside the official raw market cap; and
* no earlier authored SELL exists in that route, because Arlene's runtime
  clamp_sells pass may delete an unfillable SELL and shift later raw rows.

The resulting invariant pulses are route-choice independent and raw-index stable
under Arlene's own documented market repairs. Route-conditional pulses are
reported for research only and are not authorization to infer private intent.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ARLENE_GIT_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"
C5_ORACLE_GIT_BLOB = "a003f2cf327cf1e1d5188746823b6bada3224cab"
BUYABLE = ("WHEAT", "FERTILIZER")
SCHEMA = "titan-v4-c5-predictable-procurement/v1"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _require_blob(path: Path, expected: str, label: str) -> None:
    actual = git_blob(path.read_bytes())
    if actual != expected:
        raise ValueError(f"{label} Git blob mismatch: {actual} != {expected}")


def default_arlene_path() -> Path:
    lab = Path(__file__).resolve().parents[4]
    return lab / "reference" / "next-panel" / "vendor" / "arlene.py"


def default_c5_oracle_path() -> Path:
    return Path(__file__).resolve().with_name("c5_market_transition_oracle.py")


def load_arlene(path: Path, *, c5_oracle: Path | None = None) -> ModuleType:
    path = Path(path)
    c5_oracle = Path(c5_oracle or default_c5_oracle_path())
    _require_blob(path, ARLENE_GIT_BLOB, "Arlene")
    _require_blob(c5_oracle, C5_ORACLE_GIT_BLOB, "C5 oracle")
    spec = importlib.util.spec_from_file_location("titan_v4_c5_predictable_arlene", path)
    if spec is None or spec.loader is None:
        raise ValueError("could not load authenticated Arlene module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("routes", "MAX_ORDERS", "FINAL_EXECUTABLE_STEP", "DECISIONS"):
        if not hasattr(module, name):
            raise ValueError(f"Arlene source missing {name}")
    return module


def _plain_positive_qty(value: Any) -> int | None:
    # Engine accepts int()-coercible values, but this atlas intentionally certifies
    # only literal plain integers from the authenticated route bank.
    if type(value) is not int or value <= 0:
        return None
    return value


def _buy_at(order: Any) -> tuple[str, int] | None:
    if not isinstance(order, list) or len(order) < 3:
        return None
    if order[0] != "BUY_PRODUCT" or order[1] not in BUYABLE:
        return None
    qty = _plain_positive_qty(order[2])
    if qty is None:
        return None
    return str(order[1]), qty


def _has_unstable_sell_prefix(market: list[Any], row: int) -> bool:
    """True when Arlene may delete an earlier SELL and shift this raw row.

    In Arlene.act(), clamp_sells preserves every non-SELL row verbatim but drops
    SELL rows whose projected shed cannot fill. Therefore any preceding authored
    SELL makes the later raw index observation-dependent. We fail closed even if
    a particular replay would fill it.
    """
    for raw in market[:row]:
        if isinstance(raw, list) and raw and raw[0] == "SELL":
            return True
    return False


def _route_pulses(route: list[Any], *, route_id: str, max_orders: int,
                  final_step: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stop = min(len(route), final_step + 1)
    for step in range(stop):
        action = route[step]
        if not isinstance(action, dict):
            continue
        market = action.get("market") or []
        if not isinstance(market, list):
            continue
        capped = market[:max_orders]
        for row, raw in enumerate(capped):
            parsed = _buy_at(raw)
            if parsed is None:
                continue
            item, qty = parsed
            stable = not _has_unstable_sell_prefix(capped, row)
            out.append({
                "route": route_id,
                "step": step,
                "row": row,
                "item": item,
                "qty": qty,
                "raw_index_stable": stable,
            })
    return out


def analyze(module: ModuleType) -> dict[str, Any]:
    routes = module.routes()
    if not isinstance(routes, dict) or not routes:
        raise ValueError("Arlene routes() must return a nonempty dict")
    max_orders = getattr(module, "MAX_ORDERS")
    final_step = getattr(module, "FINAL_EXECUTABLE_STEP")
    if type(max_orders) is not int or max_orders <= 0:
        raise ValueError("MAX_ORDERS must be a positive plain int")
    if type(final_step) is not int or final_step < 0:
        raise ValueError("FINAL_EXECUTABLE_STEP must be a nonnegative plain int")

    route_ids = sorted(routes)
    per_route: dict[str, list[dict[str, Any]]] = {}
    stable_keys: dict[str, set[tuple[int, int, str, int]]] = {}
    for route_id in route_ids:
        route = routes[route_id]
        if not isinstance(route, list):
            raise ValueError(f"route {route_id!r} is not a list")
        pulses = _route_pulses(
            route,
            route_id=str(route_id),
            max_orders=max_orders,
            final_step=final_step,
        )
        per_route[str(route_id)] = pulses
        stable_keys[str(route_id)] = {
            (p["step"], p["row"], p["item"], p["qty"])
            for p in pulses if p["raw_index_stable"]
        }

    key_sets = [stable_keys[str(route_id)] for route_id in route_ids]
    invariant_keys = set.intersection(*key_sets) if key_sets else set()
    invariant = [
        {"step": step, "row": row, "item": item, "qty": qty}
        for step, row, item, qty in sorted(invariant_keys)
    ]

    conditional: list[dict[str, Any]] = []
    for route_id in route_ids:
        for p in per_route[str(route_id)]:
            key = (p["step"], p["row"], p["item"], p["qty"])
            if p["raw_index_stable"] and key not in invariant_keys:
                conditional.append(dict(p))
    conditional.sort(key=lambda p: (p["step"], p["row"], p["item"], p["qty"], p["route"]))

    all_pulses = [p for rid in route_ids for p in per_route[str(rid)]]
    stable_pulses = [p for p in all_pulses if p["raw_index_stable"]]
    decisions = []
    for raw in getattr(module, "DECISIONS"):
        if not isinstance(raw, tuple) or len(raw) != 4:
            raise ValueError("DECISIONS contains malformed entry")
        turn, feature, threshold, target = raw
        if type(turn) is not int or turn < 0 or not isinstance(feature, str):
            raise ValueError("DECISIONS contains malformed public checkpoint")
        decisions.append({
            "turn": turn,
            "feature": feature,
            "threshold": threshold,
            "target": target,
        })

    return {
        "schema": SCHEMA,
        "source": {
            "arlene_git_blob": ARLENE_GIT_BLOB,
            "c5_oracle_git_blob": C5_ORACLE_GIT_BLOB,
        },
        "scope": {
            "max_market_rows": max_orders,
            "last_executable_step": final_step,
            "buyable_items": list(BUYABLE),
            "policy_authority": "invariant_pulses_only",
            "branch_conditional_is_authority": False,
            "hidden_current_rival_action_used": False,
        },
        "route_ids": [str(r) for r in route_ids],
        "public_decisions": decisions,
        "invariant_pulses": invariant,
        "branch_conditional_pulses": conditional,
        "counts": {
            "routes": len(route_ids),
            "all_base_buy_pulses": len(all_pulses),
            "raw_index_stable_base_buy_pulses": len(stable_pulses),
            "route_invariant_pulses": len(invariant),
            "branch_conditional_stable_pulses": len(conditional),
        },
        "limits": [
            "Only exact vendored Arlene base-route BUY_PRODUCT rows are censused.",
            "Any earlier authored SELL makes a later buy row non-authoritative because clamp_sells may shift it.",
            "Branch-conditional pulses are research evidence only even though Arlene branch decisions use public observations.",
            "This atlas does not observe or infer a rival's current private action.",
            "C5/COBUY economics and current-stack collision prevalence remain separate gates.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arlene", type=Path, default=default_arlene_path())
    ap.add_argument("--c5-oracle", type=Path, default=default_c5_oracle_path())
    ap.add_argument("--output", type=Path)
    ns = ap.parse_args(argv)
    result = analyze(load_arlene(ns.arlene, c5_oracle=ns.c5_oracle))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if ns.output:
        ns.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
