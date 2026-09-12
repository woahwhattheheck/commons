#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Find source-real pocket-preload opportunities in the frozen route bank.

This is a census, not a gameplay transform.  A witness means an authored worker
returns to the shed for WHEAT/FERTILIZER between two same-day consumers even
though the earlier pickup could, in principle, carry the later refill too.
Runtime promotion still requires observed shed stock and an end-of-day capacity
certificate before any route rewrite is legal.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Iterable

SCHEMA = "titan-v5/bulk-feeder-pocket-routing/census-v1"
VENDOR_GIT_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"
MOVES = {
    "NORTH": (0, -1),
    "SOUTH": (0, 1),
    "EAST": (1, 0),
    "WEST": (-1, 0),
}
CONSUMER = {"WHEAT": "FEED", "FERTILIZER": "FERTILIZE"}
PASSIVE = {"PASS", *MOVES}

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
VENDOR = ROOT / "reference" / "next-panel" / "vendor" / "arlene.py"


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _load_vendor():
    source = VENDOR.read_bytes()
    actual = git_blob_sha1(source)
    if actual != VENDOR_GIT_BLOB:
        raise RuntimeError(
            f"frozen vendor changed: expected {VENDOR_GIT_BLOB}, got {actual}"
        )
    spec = importlib.util.spec_from_file_location("_v5_bulk_feeder_vendor", VENDOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _units(row: dict) -> list:
    if not isinstance(row, dict):
        return [["PASS"]]
    farmer = row.get("farmer")
    hands = row.get("hands")
    return [farmer if isinstance(farmer, list) and farmer else ["PASS"],
            *(hands if isinstance(hands, list) else [])]


def _unit_action(route: list, turn: int, worker: int) -> list:
    if not 0 <= turn < len(route):
        return ["PASS"]
    units = _units(route[turn])
    if worker >= len(units):
        return ["PASS"]
    action = units[worker]
    return action if isinstance(action, list) and action else ["PASS"]


def _positive_quantity(action: list) -> int | None:
    if not isinstance(action, list) or len(action) < 3:
        return None
    try:
        quantity = int(action[2])
    except (TypeError, ValueError, OverflowError):
        return None
    return quantity if quantity > 0 else None


def _pickup(action: list) -> tuple[str, int] | None:
    if not isinstance(action, list) or len(action) < 2 or action[0] != "PICKUP":
        return None
    product = action[1]
    quantity = _positive_quantity(action)
    if product not in CONSUMER or quantity is None:
        return None
    return product, quantity


def _consumer(action: list, product: str) -> bool:
    return bool(action) and action[0] == CONSUMER[product]


def _movement_summary(actions: Iterable[list]) -> dict:
    dx = dy = raw = 0
    names = []
    for action in actions:
        if action and action[0] in MOVES:
            mx, my = MOVES[action[0]]
            dx += mx
            dy += my
            raw += 1
            names.append(action[0])
    direct = abs(dx) + abs(dy)
    direct_moves = []
    if dx:
        direct_moves.extend((["EAST"] if dx > 0 else ["WEST"]) * abs(dx))
    if dy:
        direct_moves.extend((["SOUTH"] if dy > 0 else ["NORTH"]) * abs(dy))
    return {
        "raw_moves": raw,
        "direct_moves": direct,
        "backtrack_moves": raw - direct,
        "net": [dx, dy],
        "raw_path": names,
        "direct_path": [row[0] for row in direct_moves],
    }


def _worker_count(route: list, start: int, end: int) -> int:
    return max((len(_units(route[t])) for t in range(start, min(end, len(route)))), default=1)


def find_opportunities(route: list, *, route_name: str = "route", turns_per_day: int = 24) -> list[dict]:
    """Return refill segments whose second pickup can be prepaid at the first.

    Static certification is intentionally strict.  Between the consumer before
    refill and the consumer after refill, the worker may only PASS, move, and do
    that one matching PICKUP.  That makes the measured movement excess a pure
    shed-service detour rather than a hidden HARVEST/CARE/etc dependency.
    """
    if type(turns_per_day) is not int or turns_per_day <= 0:
        raise ValueError("turns_per_day must be a positive plain int")
    out = []
    for day_start in range(0, len(route), turns_per_day):
        day_end = min(len(route), day_start + turns_per_day)
        workers = _worker_count(route, day_start, day_end)
        for worker in range(workers):
            pickups = []
            for turn in range(day_start, day_end):
                parsed = _pickup(_unit_action(route, turn, worker))
                if parsed:
                    pickups.append((turn, *parsed))
            for index in range(len(pickups) - 1):
                preload_turn, product, preload_qty = pickups[index]
                refill_turn, refill_product, refill_qty = pickups[index + 1]
                if product != refill_product:
                    continue

                before = [
                    turn for turn in range(preload_turn + 1, refill_turn)
                    if _consumer(_unit_action(route, turn, worker), product)
                ]
                if not before:
                    continue
                service_before = before[-1]

                next_same_pickup = day_end
                if index + 2 < len(pickups) and pickups[index + 2][1] == product:
                    next_same_pickup = pickups[index + 2][0]
                service_after = next(
                    (
                        turn for turn in range(refill_turn + 1, next_same_pickup)
                        if _consumer(_unit_action(route, turn, worker), product)
                    ),
                    None,
                )
                if service_after is None:
                    continue

                segment_turns = list(range(service_before + 1, service_after))
                segment_actions = [_unit_action(route, turn, worker) for turn in segment_turns]
                matching_pickups = [
                    turn for turn, action in zip(segment_turns, segment_actions)
                    if _pickup(action) and _pickup(action)[0] == product
                ]
                if matching_pickups != [refill_turn]:
                    continue
                legal = True
                for turn, action in zip(segment_turns, segment_actions):
                    op = action[0] if action else "PASS"
                    if turn == refill_turn:
                        if _pickup(action) != (product, refill_qty):
                            legal = False
                            break
                    elif op not in PASSIVE:
                        legal = False
                        break
                if not legal:
                    continue

                movement = _movement_summary(segment_actions)
                # Preloading removes the refill callback itself.  Any movement
                # backtracking is additional theoretical slack that a later
                # runtime rewrite may harvest by shortening the path.
                saved_slots_upper = 1 + movement["backtrack_moves"]
                out.append({
                    "route": route_name,
                    "day": day_start // turns_per_day,
                    "worker": worker,
                    "product": product,
                    "preload_turn": preload_turn,
                    "preload_quantity_authored": preload_qty,
                    "refill_turn": refill_turn,
                    "refill_quantity_to_preload": refill_qty,
                    "service_before": service_before,
                    "service_after": service_after,
                    "segment_start": service_before + 1,
                    "segment_end": service_after - 1,
                    "same_day": True,
                    "saved_slots_upper": saved_slots_upper,
                    **movement,
                })
    return out


def scan_routes(routes: dict[str, list], *, turns_per_day: int = 24) -> dict:
    opportunities = []
    for route_name, route in sorted(routes.items()):
        opportunities.extend(
            find_opportunities(route, route_name=route_name, turns_per_day=turns_per_day)
        )
    opportunities.sort(
        key=lambda row: (-row["saved_slots_upper"], row["route"], row["refill_turn"], row["worker"])
    )
    by_product = {}
    for row in opportunities:
        by_product[row["product"]] = by_product.get(row["product"], 0) + 1
    return {
        "schema": SCHEMA,
        "vendor_git_blob": VENDOR_GIT_BLOB,
        "turns_per_day": turns_per_day,
        "routes": len(routes),
        "opportunities": opportunities,
        "opportunity_count": len(opportunities),
        "by_product": by_product,
        "max_saved_slots_upper": max(
            (row["saved_slots_upper"] for row in opportunities), default=0
        ),
        "verdict": "WITNESS" if opportunities else "NO_STATIC_WITNESS",
        "runtime_change": False,
        "production_change": False,
    }


def scan_current_routes() -> dict:
    vendor = _load_vendor()
    return scan_routes(vendor.routes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    result = scan_current_routes()
    print(json.dumps(result, sort_keys=True, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
