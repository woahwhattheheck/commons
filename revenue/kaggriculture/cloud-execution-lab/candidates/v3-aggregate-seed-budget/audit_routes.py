# SPDX-License-Identifier: Apache-2.0
"""Inventory duplicate same-crop BUY_SEED rows in the exact current route bank."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _strict_seed(row: Any) -> tuple[str, int] | None:
    if not isinstance(row, list) or len(row) < 3 or row[0] != "BUY_SEED":
        return None
    crop, quantity = row[1], row[2]
    if not isinstance(crop, str) or not crop:
        return None
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        return None
    return crop, quantity


def scan_routes(routes: dict[str, list[dict[str, Any]]], max_orders: int = 10) -> dict[str, Any]:
    duplicates: list[dict[str, Any]] = []
    tail_safe: list[dict[str, Any]] = []
    for route_name in sorted(routes):
        route = routes[route_name]
        for step, action in enumerate(route):
            market = action.get("market", []) if isinstance(action, dict) else []
            if not isinstance(market, list):
                continue
            prefix = market[:max_orders]
            by_crop: dict[str, list[dict[str, int]]] = {}
            for index, row in enumerate(prefix):
                order = _strict_seed(row)
                if order is None:
                    continue
                crop, quantity = order
                by_crop.setdefault(crop, []).append({"index": index, "quantity": quantity})
            for crop, rows in sorted(by_crop.items()):
                if len(rows) < 2:
                    continue
                record = {
                    "route": route_name,
                    "step": step,
                    "crop": crop,
                    "rows": rows,
                    "requested": sum(row["quantity"] for row in rows),
                    "active_prefix_length": len(prefix),
                }
                duplicates.append(record)

                nonempty = [i for i, row in enumerate(prefix) if row]
                if not nonempty:
                    continue
                target_index = nonempty[-1]
                target = _strict_seed(prefix[target_index])
                if target is None or target[0] != crop:
                    continue
                if all(row == [] or _strict_seed(row) is not None for row in prefix[: target_index + 1]):
                    tail_safe.append(dict(record, target_index=target_index))
    return {
        "schema": "titan-v3-aggregate-seed-route-audit/v1",
        "route_count": len(routes),
        "max_orders": max_orders,
        "duplicate_count": len(duplicates),
        "tail_safe_count": len(tail_safe),
        "duplicates": duplicates,
        "tail_safe": tail_safe,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--require-tail-safe", action="store_true")
    args = parser.parse_args()
    root = args.root
    if root is None:
        root = Path(__file__).resolve().parents[2]
    source = root / "reference" / "next-panel" / "vendor" / "arlene.py"
    arlene = _load("_granary_route_source", source)
    report = scan_routes(arlene.routes())
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(encoded, end="")
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    if args.require_tail_safe and report["tail_safe_count"] == 0:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
