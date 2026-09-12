#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""GANDER x STARVEORACLE: route-feasible alternating-feed goose cadence.

Research-only composition inside the existing opening-expansion authority.
This does not install a controller or claim economics.  It starts from the
canonical nine-goose GANDER post-EOD0 frontier and executes the exact pinned
interpreter for days 1..29 with one hired hand per day.

After the mandatory day-1 feed, odd days feed and even days skip.  Every day
collects fertilizer.  From day 4 onward, skip-feed days spend the freed FEED
slot on HARVEST, so the same two-worker geometry realizes base EGG output while
never allowing two consecutive unfed refreshes.  CARE is deliberately absent;
STARVEORACLE proves blanket alternation is not safe for CARE value.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
V4_ROOT = HERE.parents[1]
ENGINE_PATH = HERE.parents[3] / "reference" / "engine" / "kaggriculture.py"
GANDER_PATH = HERE / "goose_printer_oracle.py"
STARVE_PATH = V4_ROOT / "repairs" / "gameplay" / "dead-feed-care" / "starvation_cadence.py"

PINNED_ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
PINNED_ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
PINNED_GANDER_GIT_BLOB = "38ae7715c233c74f24aacd5fe09f4d0d7a630037"
PINNED_STARVE_GIT_BLOB = "8831ff953faf033cc6d3892c6f32ccd1ee1af06c"
GOOSE_COUNT = 9
SEASON_DAYS = 30
FIRST_SERVICE_DAY = 1
LAST_SERVICE_DAY = 29
INITIAL_WHEAT = 1000


class GanderStarveError(RuntimeError):
    pass


def _git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GanderStarveError(f"cannot load canonical source: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _direction(a: tuple[int, int], b: tuple[int, int]) -> str:
    dx, dy = b[0] - a[0], b[1] - a[1]
    table = {(1, 0): "EAST", (-1, 0): "WEST", (0, 1): "SOUTH", (0, -1): "NORTH"}
    try:
        return table[(dx, dy)]
    except KeyError as exc:
        raise GanderStarveError(f"non-adjacent route step: {a}->{b}") from exc


def _walk(a: tuple[int, int], b: tuple[int, int]) -> tuple[list[list[str]], tuple[int, int]]:
    x, y = a
    out: list[list[str]] = []
    while x != b[0]:
        nxt = (x + (1 if b[0] > x else -1), y)
        out.append([_direction((x, y), nxt)])
        x, y = nxt
    while y != b[1]:
        nxt = (x, y + (1 if b[1] > y else -1))
        out.append([_direction((x, y), nxt)])
        x, y = nxt
    return out, (x, y)


def worker_route(
    *,
    start: tuple[int, int],
    sites: Iterable[tuple[int, int]],
    feed: bool,
    harvest: bool,
) -> list[list[Any]]:
    """Materialize one daily route over the canonical GANDER site partition."""
    sites = tuple(tuple(p) for p in sites)
    if not sites:
        return []
    pos = start
    actions: list[list[Any]] = []
    if feed:
        actions.append(["PICKUP", "WHEAT", len(sites)])
    for site in sites:
        moves, pos = _walk(pos, site)
        actions.extend(moves)
        if feed:
            actions.append(["FEED"])
        actions.append(["COLLECT_FERTILIZER"])
        if harvest:
            actions.append(["HARVEST"])
    moves, pos = _walk(pos, (4, 4))
    actions.extend(moves)
    actions.append(["DROP"])
    return actions


def _canonical_sources() -> tuple[ModuleType, ModuleType]:
    # Authenticate helper bytes before import/exec.  These helpers are part of
    # the proof surface, not merely references to semantic constants.
    gander_blob = _git_blob(GANDER_PATH)
    starve_blob = _git_blob(STARVE_PATH)
    if gander_blob != PINNED_GANDER_GIT_BLOB:
        raise GanderStarveError(
            f"GANDER helper drift: expected {PINNED_GANDER_GIT_BLOB}, got {gander_blob}"
        )
    if starve_blob != PINNED_STARVE_GIT_BLOB:
        raise GanderStarveError(
            f"STARVEORACLE helper drift: expected {PINNED_STARVE_GIT_BLOB}, got {starve_blob}"
        )

    gander = _load(GANDER_PATH, "titan_v4_gander_starve_gander")
    starve = _load(STARVE_PATH, "titan_v4_gander_starve_starve")
    if getattr(gander, "EXPECTED_ENGINE_BLOB", None) != PINNED_ENGINE_GIT_BLOB:
        raise GanderStarveError("GANDER engine identity drift")
    if getattr(starve, "ENGINE_GIT_BLOB", None) != PINNED_ENGINE_GIT_BLOB:
        raise GanderStarveError("STARVEORACLE engine identity drift")
    if getattr(starve, "ENGINE_SHA256", None) != PINNED_ENGINE_SHA256:
        raise GanderStarveError("STARVEORACLE engine SHA drift")
    return gander, starve


def _route_contract(gander: ModuleType) -> dict[str, Any]:
    main_sites = tuple(tuple(p) for p in gander.MAIN_TWO_WORKER)
    hand_sites = tuple(tuple(p) for p in gander.HAND_TWO_WORKER)
    if len(main_sites) + len(hand_sites) != GOOSE_COUNT:
        raise GanderStarveError("GANDER site cardinality drift")
    if set(main_sites) & set(hand_sites):
        raise GanderStarveError("GANDER worker partitions overlap")

    feed_main = worker_route(start=(4, 4), sites=main_sites, feed=True, harvest=False)
    feed_hand = worker_route(start=(5, 4), sites=hand_sites, feed=True, harvest=False)
    skip_main = worker_route(start=(4, 4), sites=main_sites, feed=False, harvest=True)
    skip_hand = worker_route(start=(5, 4), sites=hand_sites, feed=False, harvest=True)

    authored = gander.day1_keepalive_schedule()
    authored_counts = {
        op: sum(1 for action in authored if action.op == op)
        for op in ("PICKUP", "FEED", "COLLECT_FERTILIZER", "DROP")
    }
    if authored_counts != {
        "PICKUP": 2,
        "FEED": 9,
        "COLLECT_FERTILIZER": 9,
        "DROP": 2,
    }:
        raise GanderStarveError(f"GANDER service contract drift: {authored_counts}")
    if max((action.step for action in authored), default=0) > 45:
        raise GanderStarveError("GANDER day-1 route no longer fits")
    if max(len(feed_main), len(feed_hand), len(skip_main), len(skip_hand)) > 23:
        raise GanderStarveError("composed route exceeds post-HIRE daily unit window")

    return {
        "main_sites": main_sites,
        "hand_sites": hand_sites,
        "feed_main": feed_main,
        "feed_hand": feed_hand,
        "skip_main": skip_main,
        "skip_hand": skip_hand,
        "authored_counts": authored_counts,
    }


def _inventory_total(private: Any, item: str) -> int:
    shed = private["shed"].get(item, 0)
    carried = sum(inv.get(item, 0) for inv in private["inventories"])
    return int(shed + carried)


def run_composite(*, feed_days: set[int] | None = None) -> dict[str, Any]:
    """Execute the exact interpreter from the canonical post-EOD0 GANDER state.

    ``feed_days=None`` selects the safe odd-day cadence 1,3,...,29.  Supplying a
    set is primarily for predecessor/boundary tests; no automatic repair occurs.
    """
    gander, starve = _canonical_sources()
    contract = _route_contract(gander)
    engine = starve.load_engine(ENGINE_PATH)
    state, env = starve._make_state_env(engine)
    farm = state[0].observation.farms[0]
    private = state[0].observation.private

    # Recreate the certified frontier at the exact post-EOD0 semantic boundary.
    sites = contract["main_sites"] + contract["hand_sites"]
    for x, y in sites:
        if farm["tiles"][y][x] is not None:
            raise GanderStarveError(f"GANDER site not empty at initialization: {(x, y)}")
        farm["tiles"][y][x] = engine._new_animal("GOOSE", 0)
    engine._daily_refresh_animals(farm, 0)
    if any(farm["tiles"][y][x].get("consecutive_unfed") != 1 for x, y in sites):
        raise GanderStarveError("post-EOD0 unfed boundary drift")
    if any(not farm["tiles"][y][x].get("fertilizer_available") for x, y in sites):
        raise GanderStarveError("post-EOD0 fertilizer boundary drift")

    # Preserve GANDER's actual $299 post-Day0 liquidity; daily first HIRE is $1.
    farm["money"] = 299.0
    private["shed"]["WHEAT"] = INITIAL_WHEAT

    selected_feed_days = (
        set(range(FIRST_SERVICE_DAY, LAST_SERVICE_DAY + 1, 2))
        if feed_days is None else set(feed_days)
    )
    counts = {
        "hire_orders": 0,
        "feed_attempts": 0,
        "fertilizer_collect_attempts": 0,
        "harvest_attempts": 0,
        "care_attempts": 0,
    }
    max_yield_units = 0
    max_consecutive_unfed = 1
    max_route_actions = 0
    escaped_day: int | None = None

    for day in range(FIRST_SERVICE_DAY, LAST_SERVICE_DAY + 1):
        feed = day in selected_feed_days
        # Product exists beginning after EOD3; spend the freed FEED slot on EGG
        # collection only when it can realize product.
        harvest = (not feed) and day >= 4
        main_route = worker_route(
            start=(4, 4), sites=contract["main_sites"], feed=feed, harvest=harvest
        )
        hand_route = worker_route(
            start=(5, 4), sites=contract["hand_sites"], feed=feed, harvest=harvest
        )
        max_route_actions = max(max_route_actions, len(main_route), len(hand_route))
        if max_route_actions > 23:
            raise GanderStarveError("daily route exceeds post-HIRE action window")

        counts["hire_orders"] += 1
        counts["feed_attempts"] += GOOSE_COUNT if feed else 0
        counts["fertilizer_collect_attempts"] += GOOSE_COUNT
        counts["harvest_attempts"] += GOOSE_COUNT if harvest else 0

        for hour in range(24):
            step = day * 24 + hour
            state[0].observation.step = step
            farmer_action = ["PASS"] if hour == 0 else (
                main_route[hour - 1] if hour - 1 < len(main_route) else ["PASS"]
            )
            hand_action = ["PASS"] if hour == 0 else (
                hand_route[hour - 1] if hour - 1 < len(hand_route) else ["PASS"]
            )
            market = [["HIRE"]] if hour == 0 else []
            state[0].action = {
                "farmer": farmer_action,
                "hands": [hand_action],
                "market": market,
            }
            state[1].action = {"farmer": ["PASS"], "hands": [], "market": []}
            engine.interpreter(state, env)

            living = 0
            for x, y in sites:
                tile = farm["tiles"][y][x]
                if isinstance(tile, dict) and tile.get("animal") == "GOOSE":
                    living += 1
                    max_yield_units = max(max_yield_units, int(tile.get("yield_units", 0)))
                    max_consecutive_unfed = max(
                        max_consecutive_unfed, int(tile.get("consecutive_unfed", 0))
                    )
            if living != GOOSE_COUNT:
                escaped_day = day
                break
        if escaped_day is not None:
            break

    living_tiles = [
        farm["tiles"][y][x]
        for x, y in sites
        if isinstance(farm["tiles"][y][x], dict)
        and farm["tiles"][y][x].get("animal") == "GOOSE"
    ]
    final_held_egg = sum(int(tile.get("yield_units", 0)) for tile in living_tiles)
    final_pending_fertilizer = sum(
        1 for tile in living_tiles if tile.get("fertilizer_available")
    )
    egg_total = _inventory_total(private, "EGG") + final_held_egg
    fertilizer_total = _inventory_total(private, "FERTILIZER") + final_pending_fertilizer
    wheat_remaining = _inventory_total(private, "WHEAT")
    wheat_consumed = INITIAL_WHEAT - wheat_remaining

    full_daily_feed_units = (LAST_SERVICE_DAY - FIRST_SERVICE_DAY + 1) * GOOSE_COUNT
    return {
        "schema": "titan.v4.gander-starve-composite/v1",
        "engine_git_blob": PINNED_ENGINE_GIT_BLOB,
        "engine_sha256": _sha256(ENGINE_PATH),
        "days": [FIRST_SERVICE_DAY, LAST_SERVICE_DAY],
        "feed_days": sorted(selected_feed_days),
        "skip_days": [
            day for day in range(FIRST_SERVICE_DAY, LAST_SERVICE_DAY + 1)
            if day not in selected_feed_days
        ],
        "survived": escaped_day is None and len(living_tiles) == GOOSE_COUNT,
        "escaped_day": escaped_day,
        "living_geese": len(living_tiles),
        "egg_total": egg_total,
        "fertilizer_total": fertilizer_total,
        "wheat_consumed": wheat_consumed,
        "wheat_saved_vs_feed_daily_days_1_29": full_daily_feed_units - wheat_consumed,
        "feed_actions_saved_vs_feed_daily_days_1_29": full_daily_feed_units - counts["feed_attempts"],
        "max_goose_yield_units_seen": max_yield_units,
        "max_consecutive_unfed_seen": max_consecutive_unfed,
        "final_held_egg": final_held_egg,
        "final_pending_fertilizer": final_pending_fertilizer,
        "max_route_actions_after_hire": max_route_actions,
        "action_attempts": counts,
        "source_contract": {
            "gander_frontier_geese": GOOSE_COUNT,
            "gander_helper_git_blob": _git_blob(GANDER_PATH),
            "starve_helper_git_blob": _git_blob(STARVE_PATH),
            "gander_day1_service_counts": contract["authored_counts"],
            "starve_engine_git_blob": getattr(starve, "ENGINE_GIT_BLOB"),
            "care_used": False,
            "economics_claim": False,
            "runtime_change": False,
            "default_change": False,
        },
    }


def build_report() -> dict[str, Any]:
    safe = run_composite()
    # Historical literal mistake killer: post-EOD0 geese already carry one miss,
    # so skipping day 1 causes the second miss and immediate escape.
    unsafe_feed_days = set(range(3, LAST_SERVICE_DAY + 1, 2))
    unsafe = run_composite(feed_days=unsafe_feed_days)
    if not safe["survived"]:
        raise GanderStarveError("safe composite cadence did not survive")
    if unsafe["escaped_day"] != 1:
        raise GanderStarveError("day-1 mandatory-feed boundary disappeared")
    return {
        "schema": "titan.v4.gander-starve-report/v1",
        "safe_composite": safe,
        "mandatory_day1_feed_predecessor": {
            "escaped_day": unsafe["escaped_day"],
            "survived": unsafe["survived"],
        },
        "interpretation": {
            "mechanism": (
                "after mandatory day-1 feed, alternate feed/skip; on mature skip "
                "days replace FEED with HARVEST while retaining daily fertilizer collection"
            ),
            "wheat_savings_are_units_not_cash": True,
            "care_value_modeled": False,
            "market_prices_modeled": False,
            "opponent_modeled": False,
            "promotion_decision": "NOT_ASSESSED",
        },
        "next_gate": (
            "Consume this cadence only through the existing opener/native scheduler. "
            "Run both seats versus current opponents with exact WHEAT acquisition, "
            "CARE opportunity cost, shed capacity, EGG/FERT sale timing and fallback."
        ),
    }


def main() -> int:
    try:
        report = build_report()
    except (OSError, ValueError, GanderStarveError) as exc:
        print(f"GANDER_STARVE BLOCKED: {exc}")
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
