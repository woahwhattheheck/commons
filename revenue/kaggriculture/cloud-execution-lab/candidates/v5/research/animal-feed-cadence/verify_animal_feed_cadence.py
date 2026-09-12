#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Probe the pinned engine's animal basic-needs cadence and current route surface.

This is evidence, not a runtime policy. It proves exactly what an unfed day does,
identifies the CARE/pending-bonus exclusion, and inventories FEED/PICKUP density
in the pinned Arlene route tapes so a later V5 admission rule can be evaluated
without changing the production controller or defaults.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import types
from typing import Any

ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
ARLENE_GIT_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _lab_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "reference" / "engine" / "kaggriculture.py").is_file():
            return parent
    raise RuntimeError("cloud-execution-lab root not found")


def load_engine():
    root = _lab_root()
    path = root / "reference" / "engine" / "kaggriculture.py"
    source = path.read_bytes()
    if git_blob_sha1(source) != ENGINE_GIT_BLOB:
        raise ValueError("official engine git-blob mismatch")
    if hashlib.sha256(source).hexdigest() != ENGINE_SHA256:
        raise ValueError("official engine sha256 mismatch")
    tree = ast.parse(source)
    framework_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "kaggle_environments.utils"
    ]
    if len(framework_imports) != 1:
        raise ValueError("unexpected framework import shape")
    tree.body.remove(framework_imports[0])
    module = types.ModuleType("_v5_animal_feed_cadence_engine")
    module.__file__ = str(path)
    module.resolve_episode_seed = lambda _env: 0
    exec(compile(tree, module.__file__, "exec"), module.__dict__)
    return module


def load_routes() -> dict[str, list[dict[str, Any]]]:
    root = _lab_root()
    path = root / "reference" / "next-panel" / "vendor" / "arlene.py"
    source = path.read_bytes()
    if git_blob_sha1(source) != ARLENE_GIT_BLOB:
        raise ValueError("pinned Arlene git-blob mismatch")
    spec = importlib.util.spec_from_file_location("_v5_animal_feed_cadence_arlene", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load pinned Arlene")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    routes = module.routes()
    if not isinstance(routes, dict) or not routes:
        raise ValueError("pinned Arlene routes are empty")
    return routes


def _run_days(engine, animal: str, days: int, *, feed_days: set[int], care_days: set[int]) -> dict[str, Any]:
    farm = engine._new_farm(10, 3000)
    private = engine._new_private()
    farm["farmer"] = [1, 1]
    farm["tiles"][1][1] = engine._new_animal(animal, 0)
    private["inventories"][0]["WHEAT"] = days + 4
    history = []
    for day in range(days):
        if day in care_days:
            engine._apply_unit_action(farm, private, 0, ["CARE"], 10, day, 24, 100)
        if day in feed_days:
            engine._apply_unit_action(farm, private, 0, ["FEED"], 10, day, 24, 100)
        engine._daily_refresh_animals(farm, day)
        tile = farm["tiles"][1][1]
        history.append(
            {
                "day": day,
                "alive": isinstance(tile, dict) and tile.get("animal") == animal,
                "yield_units": tile.get("yield_units") if isinstance(tile, dict) else None,
                "consecutive_unfed": tile.get("consecutive_unfed") if isinstance(tile, dict) else None,
                "pending_care_bonus": tile.get("pending_care_bonus") if isinstance(tile, dict) else None,
            }
        )
    final = farm["tiles"][1][1]
    return {
        "animal": animal,
        "days": days,
        "feed_days": sorted(feed_days),
        "care_days": sorted(care_days),
        "wheat_consumed": days + 4 - private["inventories"][0].get("WHEAT", 0),
        "alive": isinstance(final, dict) and final.get("animal") == animal,
        "yield_units": final.get("yield_units") if isinstance(final, dict) else None,
        "history": history,
    }


def animal_cases(engine) -> list[dict[str, Any]]:
    rows = []
    for animal, data in engine.ANIMALS.items():
        days = data["first_yield_day"] + 5
        daily = _run_days(engine, animal, days, feed_days=set(range(days)), care_days=set())
        alternating = _run_days(
            engine,
            animal,
            days,
            feed_days={day for day in range(days) if day % 2 == 0},
            care_days=set(),
        )
        care_daily = _run_days(
            engine,
            animal,
            days,
            feed_days=set(range(days)),
            care_days={0},
        )
        care_sparse = _run_days(
            engine,
            animal,
            days,
            feed_days={day for day in range(days) if day % 2 == 0},
            care_days={0},
        )
        production_day = data["first_yield_day"] - 1
        rows.append(
            {
                "animal": animal,
                "first_yield_day": data["first_yield_day"],
                "production_refresh_day": production_day,
                "daily": daily,
                "alternating_no_care": alternating,
                "care_daily": care_daily,
                "care_alternating": care_sparse,
                "no_care_base_yield_preserved": (
                    daily["alive"]
                    and alternating["alive"]
                    and daily["yield_units"] == alternating["yield_units"]
                ),
                "wheat_saved": daily["wheat_consumed"] - alternating["wheat_consumed"],
                "care_bonus_changes_outcome": care_daily["yield_units"] != care_sparse["yield_units"],
            }
        )
    return rows


def survival_boundary(engine) -> dict[str, Any]:
    one_miss_then_feed = _run_days(engine, "GOOSE", 2, feed_days={1}, care_days=set())
    two_misses = _run_days(engine, "GOOSE", 2, feed_days=set(), care_days=set())
    return {
        "one_miss_then_feed_alive": one_miss_then_feed["alive"],
        "one_miss_then_feed_consecutive_unfed": one_miss_then_feed["history"][-1]["consecutive_unfed"],
        "two_consecutive_misses_alive": two_misses["alive"],
        "two_consecutive_misses_final_tile": two_misses["history"][-1],
    }


def _actions(row: dict[str, Any]) -> list[list[Any]]:
    farmer = row.get("farmer") or ["PASS"]
    hands = row.get("hands") or []
    return [farmer, *hands]


def route_census(routes: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    result: dict[str, Any] = {"route_count": len(routes), "routes": {}}
    for name, route in sorted(routes.items()):
        if not isinstance(route, list):
            raise ValueError(f"route {name} is not a list")
        feed_actions = []
        care_actions = []
        wheat_pickups = []
        feed_days_by_actor: dict[int, set[int]] = {}
        for step, row in enumerate(route):
            if not isinstance(row, dict):
                raise ValueError(f"route {name} row {step} is not an object")
            for actor, action in enumerate(_actions(row)):
                if not isinstance(action, list) or not action:
                    continue
                op = action[0]
                if op == "FEED":
                    feed_actions.append({"step": step, "day": step // 24, "actor": actor})
                    feed_days_by_actor.setdefault(actor, set()).add(step // 24)
                elif op == "CARE":
                    care_actions.append({"step": step, "day": step // 24, "actor": actor})
                elif op == "PICKUP" and len(action) > 1 and action[1] == "WHEAT":
                    quantity = action[2] if len(action) > 2 else 1
                    wheat_pickups.append(
                        {"step": step, "day": step // 24, "actor": actor, "quantity": quantity}
                    )
        adjacent_feed_day_pairs = []
        for actor, days in sorted(feed_days_by_actor.items()):
            for day in sorted(days):
                if day + 1 in days:
                    adjacent_feed_day_pairs.append({"actor": actor, "day": day, "next_day": day + 1})
        result["routes"][name] = {
            "steps": len(route),
            "feed_action_count": len(feed_actions),
            "care_action_count": len(care_actions),
            "wheat_pickup_count": len(wheat_pickups),
            "wheat_pickup_requested_units": sum(
                int(row["quantity"])
                for row in wheat_pickups
                if type(row["quantity"]) is int and row["quantity"] > 0
            ),
            "adjacent_same_actor_feed_day_pairs": len(adjacent_feed_day_pairs),
            "feed_actions": feed_actions,
            "care_actions": care_actions,
            "wheat_pickups": wheat_pickups,
            "adjacent_feed_day_pairs": adjacent_feed_day_pairs,
        }
    return result


def run_probe() -> dict[str, Any]:
    engine = load_engine()
    cases = animal_cases(engine)
    boundary = survival_boundary(engine)
    routes = route_census(load_routes())
    checks = {
        "all_animals_survive_alternating_no_care": all(
            row["alternating_no_care"]["alive"] for row in cases
        ),
        "all_animals_preserve_base_yield_without_care": all(
            row["no_care_base_yield_preserved"] for row in cases
        ),
        "alternating_feed_saves_wheat": all(row["wheat_saved"] > 0 for row in cases),
        "one_miss_then_feed_recovers": (
            boundary["one_miss_then_feed_alive"]
            and boundary["one_miss_then_feed_consecutive_unfed"] == 0
        ),
        "two_consecutive_misses_escape": not boundary["two_consecutive_misses_alive"],
        "care_bonus_is_not_safe_to_skip_blindly": all(
            row["care_bonus_changes_outcome"] for row in cases
        ),
    }
    return {
        "schema": "titan-v5/animal-feed-cadence/v1",
        "engine": {"git_blob": ENGINE_GIT_BLOB, "sha256": ENGINE_SHA256},
        "producer": {"arlene_git_blob": ARLENE_GIT_BLOB},
        "hypothesis": (
            "With no CARE/pending-care obligation, one unfed day between certified feeds "
            "preserves animal survival and base production while saving WHEAT/FEED service."
        ),
        "verdict": "CONFIRMED_WITH_GUARDS" if all(checks.values()) else "UNRESOLVED",
        "checks": checks,
        "survival_boundary": boundary,
        "animal_cases": cases,
        "route_census": routes,
        "admission_guards": [
            "never allow two consecutive unfed refreshes",
            "do not skip a FEED on a day whose CARE must create a pending bonus",
            "do not skip a production-day FEED while pending_care_bonus is nonzero",
            "future FEED must be mechanically certified rather than inferred from route intent",
            "route transforms must preserve all other actors and market rows exactly",
        ],
        "runtime_change": False,
        "policy_change": False,
    }


if __name__ == "__main__":
    result = run_probe()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["verdict"] == "CONFIRMED_WITH_GUARDS" else 1)
