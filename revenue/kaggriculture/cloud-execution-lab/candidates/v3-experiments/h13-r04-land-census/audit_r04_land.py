#!/usr/bin/env python3
"""H13: exact-current structural census for R04 land timing.

This is deliberately not a gameplay-strength or cash-feasibility claim. It decodes the
current v3 R04 route bank and derives, from authored worker movement + HIRE spawns, the
first target-quadrant tile effect after each active-prefix BUY_LAND. It also records
market occupancy and SELL/HIRE rows before the first authored land purchase so a later
official-interpreter cash probe has an exact, source-bound search space.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve()
OVERLAY = HERE.parents[2] / "v3" / "overlay"
if not OVERLAY.exists():
    raise SystemExit(f"missing V3 overlay: {OVERLAY}")
sys.path.insert(0, str(OVERLAY))

from r01_tapes import load_tapes  # noqa: E402

LAND_ORDER = ("NE", "SW", "SE")
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
TILE_OPS = {
    "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP",
    "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE",
}
ANIMALS = {"GOOSE", "COW", "SHEEP"}
BOARD_SIZE = 10
TURNS_PER_DAY = 24
MAX_ORDERS = 10
FIRST_AUTHORED_LAND_STEP = 150


def _seq(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _unit(row: Mapping[str, Any], worker: int) -> list[Any]:
    hands = row.get("hands", []) or []
    raw = row.get("farmer", ["PASS"]) if worker == 0 else (
        hands[worker - 1] if worker <= len(hands) else ["PASS"]
    )
    return list(raw) if _seq(raw) and raw else ["PASS"]


def _move(pos: tuple[int, int], action: Sequence[Any]) -> tuple[int, int]:
    delta = MOVES.get(str(action[0]) if action else "PASS")
    if delta is None:
        return pos
    nxt = pos[0] + delta[0], pos[1] + delta[1]
    return nxt if 0 <= nxt[0] < BOARD_SIZE and 0 <= nxt[1] < BOARD_SIZE else pos


def _spawn(positions: Sequence[tuple[int, int]]) -> tuple[int, int]:
    half = BOARD_SIZE // 2
    access = ((half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half))
    counts = {tile: positions.count(tile) for tile in access}
    return min(access, key=lambda tile: (counts[tile], access.index(tile)))


def _quadrant(pos: tuple[int, int]) -> str:
    half = BOARD_SIZE // 2
    return ("N" if pos[1] < half else "S") + ("W" if pos[0] < half else "E")


def _market(row: Mapping[str, Any]) -> list[list[Any]]:
    answer: list[list[Any]] = []
    for raw in row.get("market", []) or []:
        if not _seq(raw):
            raise ValueError("market action must be a sequence")
        answer.append(list(raw))
    return answer[:MAX_ORDERS]


def _land_dependent(action: Sequence[Any]) -> bool:
    if not action:
        return False
    op = str(action[0])
    return op in TILE_OPS or (op == "PLACE" and len(action) > 1 and str(action[1]) in ANIMALS)


def census_route(route: Sequence[Mapping[str, Any]], route_id: int) -> dict[str, Any]:
    if len(route) != 719:
        raise AssertionError((route_id, "route length", len(route)))

    origin = (BOARD_SIZE // 2 - 1, BOARD_SIZE // 2 - 1)
    positions: list[tuple[int, int]] = [origin]
    unlocked = ["NW"]
    pending: list[dict[str, Any]] = []
    purchases: list[dict[str, Any]] = []

    for step, row in enumerate(route):
        if step % TURNS_PER_DAY == 0:
            positions = [origin]

        for worker in range(len(positions)):
            action = _unit(row, worker)
            pos = positions[worker]
            quadrant = _quadrant(pos)
            nxt = _move(pos, action)
            for item in pending:
                if item["first_move_step"] is None and action[0] in MOVES:
                    if _quadrant(nxt) == item["target_quadrant"]:
                        item["first_move_step"] = step
                if _land_dependent(action) and quadrant == item["target_quadrant"]:
                    item["effect_count"] += 1
                    if item["first_effect_step"] is None:
                        item["first_effect_step"] = step
                        item["first_effect_worker"] = worker
                        item["first_effect_action"] = list(action)
                        item["first_effect_position"] = list(pos)
            positions[worker] = nxt

        for slot, order in enumerate(_market(row)):
            if not order:
                continue
            if order[0] == "HIRE":
                positions.append(_spawn(positions))
            elif order[0] == "BUY_LAND":
                if len(unlocked) - 1 >= len(LAND_ORDER):
                    raise AssertionError((route_id, step, "too many authored BUY_LAND rows"))
                target = LAND_ORDER[len(unlocked) - 1]
                unlocked.append(target)
                item = {
                    "purchase_step": step,
                    "purchase_slot": slot,
                    "target_quadrant": target,
                    "first_move_step": None,
                    "first_effect_step": None,
                    "first_effect_worker": None,
                    "first_effect_action": None,
                    "first_effect_position": None,
                    "effect_count": 0,
                }
                pending.append(item)
                purchases.append(item)

    for item in purchases:
        effect = item["first_effect_step"]
        item["gap_to_first_effect"] = None if effect is None else effect - item["purchase_step"]

    pre150 = []
    funding_rows = []
    for step in range(0, FIRST_AUTHORED_LAND_STEP):
        market = _market(route[step])
        nonempty = [list(order) for order in market if order]
        if step >= 96:
            pre150.append({
                "step": step,
                "active_nonempty": len(nonempty),
                "append_capacity": len(market) < MAX_ORDERS,
                "ops": [str(order[0]) for order in nonempty],
            })
        for slot, order in enumerate(market):
            if order and order[0] in ("SELL", "HIRE", "BUY_PRODUCT"):
                funding_rows.append({"step": step, "slot": slot, "order": list(order)})

    first = purchases[0] if purchases else None
    return {
        "route_id": route_id,
        "purchase_steps": [item["purchase_step"] for item in purchases],
        "purchases": purchases,
        "first_land_deadline": None if first is None or first["first_effect_step"] is None
        else first["first_effect_step"] - 1,
        "pre150_rows_96_149": pre150,
        "pre150_funding_related_rows": funding_rows,
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    tapes = load_tapes()
    if len(tapes) != 13:
        raise AssertionError(("route count", len(tapes)))

    routes = [census_route(route, i) for i, route in enumerate(tapes)]
    # H12 source fact becomes a fail-closed contract: current R04 has only 150/265 land rows.
    for row in routes:
        if row["purchase_steps"] != [150, 265]:
            raise AssertionError((row["route_id"], "BUY_LAND drift", row["purchase_steps"]))

    first_effects = [row["purchases"][0]["first_effect_step"] for row in routes]
    report = {
        "schema": "titan.v31.h13.r04-land-structural-census.v1",
        "scope": "structural-only; no cash/execution/score claim",
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source": {
            "r01_tapes_sha256": sha256(OVERLAY / "r01_tapes.py"),
            "r04_full_router_sha256": sha256(OVERLAY / "r04_full_router.py"),
            "route_count": len(tapes),
            "route_lengths": sorted({len(route) for route in tapes}),
        },
        "summary": {
            "all_purchase_steps": sorted({tuple(row["purchase_steps"]) for row in routes}),
            "first_effect_steps": first_effects,
            "earliest_first_effect": min(x for x in first_effects if x is not None),
            "latest_first_effect": max(x for x in first_effects if x is not None),
            "routes_with_pre150_land_effect": sum(
                1 for x in first_effects if x is not None and x < FIRST_AUTHORED_LAND_STEP
            ),
        },
        "routes": routes,
    }
    out = HERE.with_name("H13-R04-LAND-CENSUS.json")
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["source"], sort_keys=True))
    print(json.dumps(report["summary"], sort_keys=True))
    for row in routes:
        first = row["purchases"][0]
        print(
            f"route={row['route_id']:02d} buy={first['purchase_step']}:{first['purchase_slot']} "
            f"target={first['target_quadrant']} first_move={first['first_move_step']} "
            f"first_effect={first['first_effect_step']} deadline={row['first_land_deadline']} "
            f"effect={first['first_effect_action']}@{first['first_effect_position']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
