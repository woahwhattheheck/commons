#!/usr/bin/env python3
"""Find reset/order/resource-composition candidates in every current Arlene route."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Sequence


def import_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path.resolve(strict=True))
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def op(action: Any) -> str:
    return action[0] if isinstance(action, list) and action and isinstance(action[0], str) else "MALFORMED"


def unit_rows(action: dict[str, Any]) -> list[list[Any]]:
    return [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]


def market_rows(action: dict[str, Any]) -> list[list[Any]]:
    return list(action.get("market") or [])


def analyze_route(route: list[dict[str, Any]]) -> dict[str, Any]:
    end_unit_counts: Counter[str] = Counter()
    hire_by_hour: Counter[int] = Counter()
    final_hour_hires: list[dict[str, Any]] = []
    final_hour_roundtrips: list[dict[str, Any]] = []
    relay_candidates: list[dict[str, Any]] = []
    final_hour_drops: list[dict[str, Any]] = []
    final_hour_services: list[dict[str, Any]] = []
    final_hour_markets: list[dict[str, Any]] = []

    for step, action in enumerate(route):
        hour = step % 24
        units = unit_rows(action)
        market = market_rows(action)
        market_ops = [op(row) for row in market]
        for slot, order in enumerate(market):
            if op(order) == "HIRE":
                hire_by_hour[hour] += 1
                if hour == 23:
                    final_hour_hires.append(
                        {"step": step, "day": step // 24, "slot": slot, "market": market}
                    )

        # Static evidence for within-unit-stage cross-docking: an earlier worker
        # deposits before a later worker picks up from the same shared shed.
        for earlier, source in enumerate(units):
            if op(source) not in ("DROP", "PLACE"):
                continue
            for later in range(earlier + 1, len(units)):
                destination = units[later]
                if op(destination) != "PICKUP":
                    continue
                relay_candidates.append(
                    {
                        "step": step,
                        "day": step // 24,
                        "hour": hour,
                        "source_worker": earlier,
                        "source_action": source,
                        "destination_worker": later,
                        "destination_action": destination,
                    }
                )

        if hour != 23:
            continue
        final_hour_markets.append(
            {"step": step, "day": step // 24, "market_ops": market_ops, "market": market}
        )
        sell_items = {
            row[1]
            for row in market
            if op(row) == "SELL" and len(row) >= 2 and isinstance(row[1], str)
        }
        for worker, row in enumerate(units):
            operation = op(row)
            end_unit_counts[operation] += 1
            if operation == "DROP":
                final_hour_drops.append(
                    {"step": step, "day": step // 24, "worker": worker, "market": market}
                )
            if operation == "PICKUP":
                item = row[1] if len(row) >= 2 else None
                final_hour_roundtrips.append(
                    {
                        "step": step,
                        "day": step // 24,
                        "worker": worker,
                        "action": row,
                        "same_item_sale": item in sell_items,
                        "market": market,
                    }
                )
            if operation in ("CARE", "FEED", "HARVEST", "COLLECT_FERTILIZER", "WATER", "FERTILIZE"):
                final_hour_services.append(
                    {"step": step, "day": step // 24, "worker": worker, "action": row}
                )

    return {
        "steps": len(route),
        "hire_by_hour": {str(key): hire_by_hour[key] for key in sorted(hire_by_hour)},
        "final_hour_hires": final_hour_hires,
        "final_hour_hire_count": len(final_hour_hires),
        "final_hour_unit_counts": dict(sorted(end_unit_counts.items())),
        "final_hour_pickups": final_hour_roundtrips,
        "final_hour_pickup_count": len(final_hour_roundtrips),
        "final_hour_pickups_without_same_item_sale": sum(
            not row["same_item_sale"] for row in final_hour_roundtrips
        ),
        "final_hour_drops": final_hour_drops,
        "final_hour_drop_count": len(final_hour_drops),
        "final_hour_services": final_hour_services,
        "same_step_deposit_then_pickup": relay_candidates,
        "same_step_deposit_then_pickup_count": len(relay_candidates),
        "final_hour_markets": final_hour_markets,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arlene", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    arlene = import_path(args.arlene, "w14_route_pattern_arlene")
    routes = {
        name: analyze_route(rows)
        for name, rows in sorted(arlene.routes().items())
    }
    report = {
        "schema_version": 1,
        "operation": "titan-frontier-W14-realized-rule-composition-20260909-01",
        "source_commit": args.source_commit,
        "archive_sha256": args.archive_sha256,
        "arlene_sha256": sha256(args.arlene),
        "routes": routes,
        "aggregate": {
            "routes": len(routes),
            "final_hour_hires": sum(row["final_hour_hire_count"] for row in routes.values()),
            "final_hour_pickups": sum(row["final_hour_pickup_count"] for row in routes.values()),
            "final_hour_pickups_without_same_item_sale": sum(
                row["final_hour_pickups_without_same_item_sale"] for row in routes.values()
            ),
            "final_hour_drops": sum(row["final_hour_drop_count"] for row in routes.values()),
            "same_step_deposit_then_pickup": sum(
                row["same_step_deposit_then_pickup_count"] for row in routes.values()
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps(report["aggregate"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
