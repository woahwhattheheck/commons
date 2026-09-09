#!/usr/bin/env python3
"""Engine-grounded census of compositional economic mechanics for Titan W14."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Sequence


OPERATION = "titan-frontier-W14-realized-rule-composition-20260909-01"


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


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def route_census(arlene) -> dict[str, Any]:
    routes = arlene.routes()
    result: dict[str, Any] = {}
    for route_name, rows in sorted(routes.items()):
        unit_counts: Counter[str] = Counter()
        market_counts: Counter[str] = Counter()
        care_rows: list[dict[str, Any]] = []
        service_rows: list[dict[str, Any]] = []
        for step, action in enumerate(rows):
            units = [
                action.get("farmer") or ["PASS"],
                *(action.get("hands") or []),
            ]
            for worker, unit in enumerate(units):
                op = unit[0] if isinstance(unit, list) and unit else "MALFORMED"
                unit_counts[op] += 1
                if op == "CARE":
                    care_rows.append({"step": step, "day": step // 24, "hour": step % 24, "worker": worker})
                if op in ("FEED", "CARE", "HARVEST", "COLLECT_FERTILIZER"):
                    service_rows.append(
                        {
                            "step": step,
                            "day": step // 24,
                            "hour": step % 24,
                            "worker": worker,
                            "op": op,
                        }
                    )
            for order in action.get("market") or []:
                op = order[0] if isinstance(order, list) and order else "MALFORMED"
                market_counts[op] += 1
        result[route_name] = {
            "steps": len(rows),
            "unit_action_counts": dict(sorted(unit_counts.items())),
            "market_order_counts": dict(sorted(market_counts.items())),
            "care_count": len(care_rows),
            "care_rows": care_rows,
            "animal_service_rows": service_rows,
        }
    return result


def new_single_animal_farm(engine, animal: str, placed_day: int = 0):
    tile = engine._new_animal(animal, placed_day)
    return {"tiles": [[tile]]}


def simulate_policy(
    engine,
    animal: str,
    *,
    days: int,
    care_days: set[int],
    feed_days: set[int],
    harvest_days: set[int],
    initial_yield: int = 0,
    initial_pending: int = 0,
) -> dict[str, Any]:
    farm = new_single_animal_farm(engine, animal)
    tile = farm["tiles"][0][0]
    tile["yield_units"] = initial_yield
    tile["pending_care_bonus"] = initial_pending
    harvested = 0
    timeline: list[dict[str, Any]] = []
    for day in range(days):
        tile = farm["tiles"][0][0]
        if not isinstance(tile, dict) or "animal" not in tile:
            timeline.append({"day": day, "escaped": True})
            break
        before = {
            "yield_units": tile["yield_units"],
            "pending_care_bonus": tile.get("pending_care_bonus", 0),
            "consecutive_unfed": tile["consecutive_unfed"],
        }
        harvested_today = 0
        if day in harvest_days and tile["yield_units"] > 0:
            harvested_today = tile["yield_units"]
            harvested += harvested_today
            tile["yield_units"] = 0
        tile["fed_today"] = day in feed_days
        tile["cared_today"] = day in care_days
        engine._daily_refresh_animals(farm, day)
        after_tile = farm["tiles"][0][0]
        timeline.append(
            {
                "day": day,
                "next_day": day + 1,
                "fed": day in feed_days,
                "cared": day in care_days,
                "harvested_before_refresh": harvested_today,
                "before": before,
                "after": (
                    {
                        "yield_units": after_tile["yield_units"],
                        "pending_care_bonus": after_tile.get("pending_care_bonus", 0),
                        "consecutive_unfed": after_tile["consecutive_unfed"],
                    }
                    if isinstance(after_tile, dict) and "animal" in after_tile
                    else {"escaped": True}
                ),
            }
        )
    tile = farm["tiles"][0][0]
    held = tile.get("yield_units", 0) if isinstance(tile, dict) else 0
    return {
        "animal": animal,
        "days": days,
        "care_days": sorted(care_days),
        "feed_days": sorted(feed_days),
        "harvest_days": sorted(harvest_days),
        "harvested": harvested,
        "held": held,
        "total_product": harvested + held,
        "timeline": timeline,
    }


def care_cases(engine) -> dict[str, Any]:
    cases: dict[str, Any] = {}
    for animal, data in engine.ANIMALS.items():
        first = int(data["first_yield_day"])
        interval = int(data["interval"])
        horizon = first + interval * 2 + 1
        feed_all = set(range(horizon))
        harvest = set(range(first, horizon))
        baseline = simulate_policy(
            engine,
            animal,
            days=horizon,
            care_days=set(),
            feed_days=feed_all,
            harvest_days=harvest,
        )
        cared = simulate_policy(
            engine,
            animal,
            days=horizon,
            care_days=set(range(horizon)),
            feed_days=feed_all,
            harvest_days=harvest,
        )
        first_fill = simulate_policy(
            engine,
            animal,
            days=first + 1,
            care_days=set(range(max(0, int(data["max_held"]) - 1))),
            feed_days=set(range(first)),
            harvest_days={first},
        )
        missed_feed = simulate_policy(
            engine,
            animal,
            days=first,
            care_days=set(range(max(0, first - 1))),
            feed_days=set(range(max(0, first - 1))),
            harvest_days=set(),
        )
        near_cap = simulate_policy(
            engine,
            animal,
            days=first,
            care_days={max(0, first - 2)},
            feed_days=set(range(first)),
            harvest_days=set(),
            initial_yield=max(0, int(data["max_held"]) - 1),
            initial_pending=1,
        )
        product = data["product"]
        base_price = int(engine.MARKET_PARAMS[product]["base"])
        cases[animal] = {
            "product": product,
            "base_price": base_price,
            "first_yield_day": first,
            "interval_days": interval,
            "max_held": int(data["max_held"]),
            "feed_only": baseline,
            "care_every_fed_day": cared,
            "first_fill_minimal_care": first_fill,
            "countercase_unfed_production_refresh": missed_feed,
            "countercase_near_hold_cap": near_cap,
            "steady_horizon_marginal_product": cared["total_product"] - baseline["total_product"],
            "steady_horizon_marginal_base_value": (
                cared["total_product"] - baseline["total_product"]
            )
            * base_price,
            "care_actions": len(cared["care_days"]),
        }
    sheep = engine.ANIMALS["SHEEP"]
    minimal = simulate_policy(
        engine,
        "SHEEP",
        days=6,
        care_days={0, 1, 2, 3, 4},
        feed_days={0, 1, 2, 3, 4, 5},
        harvest_days=set(),
    )
    no_care = simulate_policy(
        engine,
        "SHEEP",
        days=6,
        care_days=set(),
        feed_days={0, 1, 2, 3, 4, 5},
        harvest_days=set(),
    )
    if minimal["held"] != sheep["max_held"] or no_care["held"] != 1:
        raise AssertionError(
            f"unexpected SHEEP care recurrence: minimal={minimal['held']}, baseline={no_care['held']}"
        )
    unfed = simulate_policy(
        engine,
        "SHEEP",
        days=6,
        care_days={0, 1, 2, 3, 4},
        feed_days={0, 1, 2, 3, 4},
        harvest_days=set(),
    )
    if unfed["held"] != 1 or unfed["timeline"][-1]["after"].get("pending_care_bonus") != 0:
        raise AssertionError("unfed production-day countercase no longer discards care stack")
    cases["_anchor"] = {
        "sheep_five_cares_then_fed_first_production_units": minimal["held"],
        "sheep_feed_only_first_production_units": no_care["held"],
        "sheep_five_cares_but_unfed_first_production_units": unfed["held"],
        "marginal_wool_units": minimal["held"] - no_care["held"],
        "marginal_base_value": (
            minimal["held"] - no_care["held"]
        )
        * int(engine.MARKET_PARAMS["WOOL"]["base"]),
    }
    return cases


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--arlene", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    loader = import_path(args.loader, "w14_official_loader")
    engine, engine_hashes = loader.get_engine(args.engine_dir)
    arlene = import_path(args.arlene, "w14_arlene")
    routes = route_census(arlene)
    cases = care_cases(engine)
    report = {
        "schema_version": 1,
        "operation": OPERATION,
        "source_commit": args.source_commit,
        "archive_sha256": args.archive_sha256,
        "loader": {"path": str(args.loader), "sha256": sha256(args.loader)},
        "engine_ref": loader.ENGINE_REF,
        "engine_sha256": engine_hashes,
        "arlene": {"path": str(args.arlene), "sha256": sha256(args.arlene)},
        "route_census": routes,
        "care_cases": cases,
        "conclusion_gate": {
            "all_routes_zero_care": all(row["care_count"] == 0 for row in routes.values()),
            "engine_anchor_marginal_wool_units": cases["_anchor"]["marginal_wool_units"],
            "engine_anchor_marginal_base_value": cases["_anchor"]["marginal_base_value"],
            "full_game_realization_proven": False,
            "default_activation_authorized": False,
        },
    }
    atomic_json(args.output, report)
    print(json.dumps(report["conclusion_gate"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
