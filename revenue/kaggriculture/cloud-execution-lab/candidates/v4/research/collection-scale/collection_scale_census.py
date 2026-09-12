"""Route-bank census for Titan V4 animal collection scale.

Research-only: this module measures authored route structure.  It never mutates
actions, runtime, defaults, archives, or production pointers.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Iterable

ANIMALS = ("GOOSE", "COW", "SHEEP")
ANIMAL_PRODUCTS = ("EGG", "MILK", "WOOL")
UNIT_OPS = (
    "BUILD_COOP",
    "BUILD_PASTURE",
    "PLACE",
    "FEED",
    "CARE",
    "HARVEST",
    "COLLECT_FERTILIZER",
    "PASS",
)
MARKET_OPS = ("BUY_ANIMAL", "HIRE", "SELL")


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def _unit_rows(action: Any) -> list[list[Any]]:
    if not isinstance(action, dict):
        return []
    rows: list[list[Any]] = []
    farmer = action.get("farmer")
    if isinstance(farmer, list):
        rows.append(farmer)
    hands = action.get("hands")
    if isinstance(hands, list):
        rows.extend(row for row in hands if isinstance(row, list))
    return rows


def _market_rows(action: Any, max_orders: int) -> list[list[Any]]:
    if not isinstance(action, dict):
        return []
    market = action.get("market")
    if not isinstance(market, list):
        return []
    return [row for row in market[:max_orders] if isinstance(row, list)]


def _positive_quantity(row: list[Any], index: int = 2) -> int:
    if len(row) <= index:
        return 1
    try:
        value = int(row[index])
    except (TypeError, ValueError):
        return 0
    return max(0, value)


def _record_span(spans: dict[str, list[int]], key: str, step: int) -> None:
    pair = spans.setdefault(key, [step, step])
    pair[0] = min(pair[0], step)
    pair[1] = max(pair[1], step)


def census_route(route: Iterable[Any], *, max_orders: int = 10) -> dict[str, Any]:
    """Count authored animal-production operations in one decoded route."""
    if max_orders <= 0:
        raise ValueError("max_orders must be positive")

    unit = Counter()
    market = Counter()
    animal_buys = Counter()
    product_sells = Counter()
    placement = Counter()
    spans: dict[str, list[int]] = {}
    step_count = 0
    actor_rows = 0

    for step, action in enumerate(route):
        step_count = step + 1
        for row in _unit_rows(action):
            actor_rows += 1
            op = row[0] if row else "PASS"
            if not isinstance(op, str):
                continue
            unit[op] += 1
            if op in UNIT_OPS:
                _record_span(spans, f"unit:{op}", step)
            if op == "PLACE" and len(row) > 1 and row[1] in ANIMALS:
                placement[str(row[1])] += _positive_quantity(row)
                _record_span(spans, f"place:{row[1]}", step)

        for row in _market_rows(action, max_orders):
            if not row or not isinstance(row[0], str):
                continue
            op = row[0]
            market[op] += 1
            if op in MARKET_OPS:
                _record_span(spans, f"market:{op}", step)
            if op == "BUY_ANIMAL" and len(row) > 1 and row[1] in ANIMALS:
                animal = str(row[1])
                animal_buys[animal] += _positive_quantity(row)
                _record_span(spans, f"buy:{animal}", step)
            elif op == "SELL" and len(row) > 1 and row[1] in ANIMAL_PRODUCTS:
                product = str(row[1])
                product_sells[product] += _positive_quantity(row)
                _record_span(spans, f"sell:{product}", step)

    bought = sum(animal_buys.values())
    placed = sum(placement.values())
    harvest = unit.get("HARVEST", 0)
    feed = unit.get("FEED", 0)
    care = unit.get("CARE", 0)
    collect_fertilizer = unit.get("COLLECT_FERTILIZER", 0)
    service = feed + care + harvest + collect_fertilizer

    def per_animal(n: int) -> float | None:
        return round(n / bought, 6) if bought else None

    return {
        "steps": step_count,
        "actor_rows": actor_rows,
        "unit_ops": dict(sorted(unit.items())),
        "market_ops": dict(sorted(market.items())),
        "animal_buys": {a: animal_buys.get(a, 0) for a in ANIMALS},
        "animal_placements": {a: placement.get(a, 0) for a in ANIMALS},
        "animal_product_sell_units": {p: product_sells.get(p, 0) for p in ANIMAL_PRODUCTS},
        "totals": {
            "animals_bought": bought,
            "animals_placed": placed,
            "harvest_rows": harvest,
            "feed_rows": feed,
            "care_rows": care,
            "collect_fertilizer_rows": collect_fertilizer,
            "animal_service_rows": service,
        },
        "ratios_per_animal_bought": {
            "placements": per_animal(placed),
            "harvest_rows": per_animal(harvest),
            "feed_rows": per_animal(feed),
            "care_rows": per_animal(care),
            "service_rows": per_animal(service),
        },
        "spans": {key: value for key, value in sorted(spans.items())},
    }


def census_routes(routes: dict[str, Iterable[Any]], *, max_orders: int = 10) -> dict[str, Any]:
    """Return per-route census plus deltas that isolate route-family variation."""
    if not isinstance(routes, dict) or not routes:
        raise ValueError("routes must be a non-empty mapping")
    per_route = {
        str(route_id): census_route(route, max_orders=max_orders)
        for route_id, route in sorted(routes.items(), key=lambda item: str(item[0]))
    }

    metric_keys = (
        "animals_bought",
        "animals_placed",
        "harvest_rows",
        "feed_rows",
        "care_rows",
        "collect_fertilizer_rows",
        "animal_service_rows",
    )
    ranges = {}
    for key in metric_keys:
        vals = {rid: row["totals"][key] for rid, row in per_route.items()}
        lo = min(vals.values())
        hi = max(vals.values())
        ranges[key] = {
            "min": lo,
            "max": hi,
            "spread": hi - lo,
            "min_routes": sorted(rid for rid, value in vals.items() if value == lo),
            "max_routes": sorted(rid for rid, value in vals.items() if value == hi),
        }

    buy_species_ranges = {}
    for animal in ANIMALS:
        vals = {rid: row["animal_buys"][animal] for rid, row in per_route.items()}
        lo, hi = min(vals.values()), max(vals.values())
        buy_species_ranges[animal] = {"min": lo, "max": hi, "spread": hi - lo}

    return {
        "schema": "titan-v4-collection-scale-census-v1",
        "research_only": True,
        "decision_authority": False,
        "collection_semantics": {
            "animal_product_action": "HARVEST",
            "fertilizer_action": "COLLECT_FERTILIZER",
        },
        "routes": per_route,
        "route_family_ranges": ranges,
        "animal_buy_ranges": buy_species_ranges,
    }


def load_parent(path: Path):
    spec = importlib.util.spec_from_file_location("_herdwork_parent", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load parent source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--expected-git-blob", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    parent_path = args.parent.resolve()
    actual = git_blob_sha1(parent_path)
    if actual != args.expected_git_blob:
        raise SystemExit(
            f"parent source drift: expected {args.expected_git_blob}, got {actual}"
        )
    parent = load_parent(parent_path)
    routes = parent.routes()
    result = census_routes(routes, max_orders=int(getattr(parent, "MAX_ORDERS", 10)))
    result["parent"] = str(parent_path)
    result["parent_git_blob"] = actual
    result["route_ids"] = sorted(str(rid) for rid in routes)

    text = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
