#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Audit FrozenSelected's future-unit projection against official atomic PLANT semantics.

This is an evidence tool, not a gameplay claim. It:
1. binds the exact source bytes it imports;
2. inventories every repeated same-crop PLANT row in the four current route tapes;
3. proves the current sequential helper and the official atomic rule differ;
4. proves that difference can reach the helper's returned acquisition certificate; and
5. emits a fail-closed machine-readable disposition.

The official interpreter counts all same-crop PLANT requests before applying any unit
action. When demand exceeds available seeds, *all* requests for that crop become PASS.
FrozenSelected._funding_trace currently calls _apply_unit_action one actor at a time.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import frozen_selected as frozen  # noqa: E402
import mechanics as mechanics  # noqa: E402

SOURCE_PATHS = (
    "frozen_selected.py",
    "mechanics.py",
    "reference/engine/kaggriculture.py",
    "reference/next-panel/vendor/arlene.py",
)


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unit_actions(action: dict[str, Any]) -> list[list[Any]]:
    farmer = action.get("farmer", ["PASS"])
    hands = action.get("hands", [])
    if not isinstance(farmer, list):
        farmer = ["PASS"]
    if not isinstance(hands, list):
        hands = []
    return [farmer, *[a if isinstance(a, list) else ["PASS"] for a in hands]]


def blocked_plant_crops(
    actions: Iterable[list[Any]], seeds: dict[str, Any]
) -> set[str]:
    demand: Counter[str] = Counter()
    for action in actions:
        if (
            isinstance(action, list)
            and len(action) >= 2
            and action[0] == "PLANT"
            and isinstance(action[1], str)
        ):
            demand[action[1]] += 1
    return {
        crop
        for crop, quantity in demand.items()
        if quantity > int(seeds.get(crop, 0))
    }


def apply_unit_stage(
    farm: dict[str, Any],
    private: dict[str, Any],
    action: dict[str, Any],
    *,
    step: int,
    atomic_plants: bool,
    shed_capacity: int = 10**6,
) -> set[str]:
    """Apply one unit stage using current sequential or official atomic PLANT rules."""
    actions = unit_actions(action)
    blocked = (
        blocked_plant_crops(actions, private.get("seeds", {}))
        if atomic_plants
        else set()
    )
    for actor, raw in enumerate(actions):
        selected = (
            ["PASS"]
            if (
                len(raw) >= 2
                and raw[0] == "PLANT"
                and raw[1] in blocked
            )
            else raw
        )
        mechanics._apply_unit_action(
            farm,
            private,
            actor,
            selected,
            len(farm["tiles"]),
            int(step) // 24,
            24,
            shed_capacity,
        )
    return blocked


def projection_trace(
    obs: dict[str, Any],
    config: dict[str, Any],
    farm: dict[str, Any],
    private: dict[str, Any],
    route: list[dict[str, Any]],
    now: int,
    end: int,
    current_market: list[list[Any]],
    *,
    stress_units: int = 0,
    atomic_plants: bool,
) -> dict[str, Any]:
    """Mirror current _funding_trace, varying only the future unit-stage rule."""
    f, p = copy.deepcopy(farm), copy.deepcopy(private)
    inventory = {
        key: int(value) for key, value in obs["market"]["inventory"].items()
    }
    params = obs["market"].get("params")
    cap = int(config.get("shedCapacity", 100))
    max_orders = int(config.get("maxMarketOrdersPerTurn", 10))
    hires = int(f.get("hires_today", 0))
    buy_items: set[str] = set()
    for step in range(now, end + 1):
        orders = (
            current_market
            if step == now
            else (
                route[step].get("market", [])
                if step < len(route)
                else []
            )
        )
        for order in orders[:max_orders]:
            if (
                order
                and len(order) > 2
                and order[0] == "BUY_PRODUCT"
            ):
                buy_items.add(order[1])
    if stress_units:
        for item in buy_items:
            inventory[item] = inventory.get(item, 0) - int(stress_units)

    acquisitions: list[tuple[tuple[Any, ...], int]] = []
    executed_sales: list[tuple[int, str, int, int]] = []
    blocked_events: list[dict[str, Any]] = []

    for step in range(now, end + 1):
        if step > now:
            action = route[step] if step < len(route) else frozen.parent.PASS
            blocked = apply_unit_stage(
                f,
                p,
                action,
                step=step,
                atomic_plants=atomic_plants,
                shed_capacity=10**6,
            )
            if blocked:
                blocked_events.append(
                    {
                        "step": step,
                        "blocked_crops": sorted(blocked),
                        "seed_stock": {
                            crop: int(p["seeds"].get(crop, 0))
                            for crop in sorted(blocked)
                        },
                    }
                )
        if step > now and step % 24 == 0:
            hires = 0

        orders = (
            current_market
            if step == now
            else (
                route[step].get("market", [])
                if step < len(route)
                else []
            )
        )
        for index, order in enumerate(orders[:max_orders]):
            if not order:
                continue
            op = order[0]
            item = order[1] if len(order) > 1 else ""
            requested = max(0, int(order[2])) if len(order) > 2 else 1
            executed = 0

            if op == "SELL" and len(order) > 2:
                cash = 0
                for _ in range(requested):
                    if p["shed"].get(item, 0) <= 0:
                        break
                    price = mechanics.market_price(
                        item, inventory[item], params
                    )
                    p["shed"][item] -= 1
                    f["money"] += price
                    cash += price
                    executed += 1
                    if price > 1:
                        inventory[item] += 1
                if step > now:
                    executed_sales.append((step, item, executed, cash))
            elif op == "HIRE":
                price = mechanics._hire_cost(
                    hires, int(config.get("farmHandCostMult", 1))
                )
                if f["money"] >= price:
                    f["money"] -= price
                    hires += 1
                    executed = 1
                    f["hands"].append(
                        mechanics._spawn_hand(f, len(f["tiles"]))
                    )
                    p["inventories"].append({})
                acquisitions.append(((step, index, op, ""), executed))
            elif op == "BUY_LAND":
                land_index = len(f["unlocked_quadrants"]) - 1
                price = (
                    mechanics.LAND_PRICES[land_index]
                    if land_index < len(mechanics.LAND_PRICES)
                    else 0
                )
                if f["money"] >= price:
                    f["money"] -= price
                    executed = 1
                    if len(f["unlocked_quadrants"]) <= len(
                        mechanics.LAND_ORDER
                    ):
                        f["unlocked_quadrants"].append(
                            mechanics.LAND_ORDER[
                                len(f["unlocked_quadrants"]) - 1
                            ]
                        )
                acquisitions.append(((step, index, op, ""), executed))
            elif (
                op == "BUY_SEED"
                and len(order) > 2
                and item in mechanics.CROPS
            ):
                price = int(mechanics.CROPS[item]["seed"])
                for _ in range(requested):
                    if f["money"] < price:
                        break
                    f["money"] -= price
                    p["seeds"][item] = p["seeds"].get(item, 0) + 1
                    executed += 1
                acquisitions.append(((step, index, op, item), executed))
            elif (
                op == "BUY_ANIMAL"
                and len(order) > 2
                and item in mechanics.ANIMALS
            ):
                price = int(mechanics.ANIMALS[item]["cost"])
                for _ in range(requested):
                    if (
                        f["money"] < price
                        or sum(p["shed"].values()) >= cap
                    ):
                        break
                    f["money"] -= price
                    p["shed"][item] = p["shed"].get(item, 0) + 1
                    executed += 1
                acquisitions.append(((step, index, op, item), executed))
            elif (
                op == "BUY_PRODUCT"
                and len(order) > 2
                and item in mechanics.PRODUCTS
            ):
                for _ in range(requested):
                    if sum(p["shed"].values()) >= cap:
                        break
                    price = mechanics.market_price(
                        item, inventory[item] - 1, params
                    )
                    if f["money"] < price:
                        break
                    f["money"] -= price
                    inventory[item] -= 1
                    p["shed"][item] = p["shed"].get(item, 0) + 1
                    executed += 1
                acquisitions.append(((step, index, op, item), executed))

    return {
        "cash": int(f["money"]),
        "acquisitions": acquisitions,
        "executed_sales": executed_sales,
        "blocked_plant_events": blocked_events,
        "ending_seed_stock": {
            key: int(value) for key, value in sorted(p["seeds"].items())
        },
        "ending_shed_total": int(sum(p["shed"].values())),
        "state_sha256": hashlib.sha256(
            canonical_json({"farm": f, "private": p, "inventory": inventory})
        ).hexdigest(),
    }


def _blank_farm() -> dict[str, Any]:
    size = 10
    tiles = [
        [
            None if x < size // 2 and y < size // 2 else "LOCKED"
            for x in range(size)
        ]
        for y in range(size)
    ]
    return {
        "money": 1_000.0,
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [[3, 4]],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }


def _blank_private() -> dict[str, Any]:
    shed = {
        item: 0
        for item in [
            *mechanics.PRODUCTS,
            *mechanics.ANIMALS.keys(),
        ]
    }
    shed["WHEAT"] = 99
    return {
        "shed": shed,
        "seeds": {
            crop: (1 if crop == "WHEAT" else 0)
            for crop in mechanics.CROPS
        },
        "inventories": [{"COW": 1}, {}],
    }


def downstream_witness() -> dict[str, Any]:
    """A minimized trace where the unit-stage mismatch changes a funded acquisition."""
    pass_row = {
        "farmer": ["PASS"],
        "hands": [["PASS"]],
        "market": [],
    }
    route = [
        copy.deepcopy(pass_row),
        {
            "farmer": ["PLANT", "WHEAT"],
            "hands": [["PLANT", "WHEAT"]],
            "market": [],
        },
        {
            "farmer": ["BUILD_PASTURE"],
            "hands": [["PASS"]],
            "market": [],
        },
        {
            "farmer": ["PLACE", "COW"],
            "hands": [["PASS"]],
            "market": [],
        },
        {
            "farmer": ["PASS"],
            "hands": [["PASS"]],
            "market": [["BUY_ANIMAL", "SHEEP", 1]],
        },
    ]
    market_inventory = {
        item: 10_000 for item in mechanics.PRODUCTS
    }
    obs = {
        "step": 0,
        "player": 0,
        "market": {"inventory": market_inventory},
    }
    config = {
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1,
    }
    farm = _blank_farm()
    private = _blank_private()
    sequential = frozen._funding_trace(
        obs,
        config,
        copy.deepcopy(farm),
        copy.deepcopy(private),
        route,
        0,
        4,
        [],
        stress_units=0,
    )
    mirrored_sequential = projection_trace(
        obs,
        config,
        farm,
        private,
        route,
        0,
        4,
        [],
        stress_units=0,
        atomic_plants=False,
    )
    atomic = projection_trace(
        obs,
        config,
        farm,
        private,
        route,
        0,
        4,
        [],
        stress_units=0,
        atomic_plants=True,
    )
    if sequential != {
        "cash": mirrored_sequential["cash"],
        "acquisitions": mirrored_sequential["acquisitions"],
        "executed_sales": mirrored_sequential["executed_sales"],
    }:
        raise AssertionError(
            "local mirror drifted from current FrozenSelected._funding_trace"
        )
    key = (4, 0, "BUY_ANIMAL", "SHEEP")
    seq_fills = dict(sequential["acquisitions"]).get(key)
    atomic_fills = dict(atomic["acquisitions"]).get(key)
    return {
        "route": route,
        "sequential": sequential,
        "atomic": atomic,
        "target_acquisition": list(key),
        "sequential_fill": seq_fills,
        "atomic_fill": atomic_fills,
        "changed": sequential != {
            "cash": atomic["cash"],
            "acquisitions": atomic["acquisitions"],
            "executed_sales": atomic["executed_sales"],
        },
    }


def route_census() -> dict[str, Any]:
    controller = frozen.parent.Agent()
    routes = getattr(controller, "R", None)
    if not isinstance(routes, dict) or not routes:
        raise RuntimeError("current parent route bank is absent or malformed")
    rows: list[dict[str, Any]] = []
    route_lengths: dict[str, int] = {}
    for route_id, route in sorted(routes.items()):
        if not isinstance(route, (list, tuple)):
            raise RuntimeError(f"route {route_id!r} is not a sequence")
        route_lengths[str(route_id)] = len(route)
        for step, row in enumerate(route):
            if not isinstance(row, dict):
                raise RuntimeError(
                    f"route {route_id!r} step {step} is not a dict"
                )
            counts: Counter[str] = Counter()
            actors: dict[str, list[int]] = {}
            for actor, action in enumerate(unit_actions(row)):
                if (
                    len(action) >= 2
                    and action[0] == "PLANT"
                    and isinstance(action[1], str)
                ):
                    crop = action[1]
                    counts[crop] += 1
                    actors.setdefault(crop, []).append(actor)
            for crop, quantity in sorted(counts.items()):
                if quantity >= 2:
                    rows.append(
                        {
                            "route_id": str(route_id),
                            "step": step,
                            "crop": crop,
                            "demand": quantity,
                            "actors": actors[crop],
                            "row_sha256": hashlib.sha256(
                                canonical_json(row)
                            ).hexdigest(),
                        }
                    )
    return {
        "route_count": len(routes),
        "route_lengths": route_lengths,
        "repeated_same_crop_plant_rows": rows,
        "repeated_row_count": len(rows),
    }


def build_report() -> dict[str, Any]:
    sources = {
        relative: {
            "raw_sha256": raw_sha256(ROOT / relative),
            "bytes": (ROOT / relative).stat().st_size,
        }
        for relative in SOURCE_PATHS
    }
    census = route_census()
    witness = downstream_witness()
    synthetic_pass = (
        witness["changed"]
        and witness["sequential_fill"] == 0
        and witness["atomic_fill"] == 1
    )
    if not synthetic_pass:
        disposition = "INVALID"
        reason = "minimized downstream witness did not reproduce"
    elif census["repeated_row_count"] == 0:
        disposition = "DORMANT"
        reason = "current route bank has no repeated same-crop PLANT row"
    else:
        disposition = "ROUTE_RISK"
        reason = (
            "current routes contain necessary repeated PLANT rows; "
            "observation-bound activation is still required before games"
        )
    return {
        "schema": "titan-v3-frozen-atomic-projection-audit-v1",
        "source": sources,
        "route_census": census,
        "downstream_witness": witness,
        "synthetic_contract_pass": synthetic_pass,
        "disposition": disposition,
        "reason": reason,
        "score_claim": False,
        "canonical_mutation_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if report["disposition"] == "INVALID":
        return 2
    if report["disposition"] == "DORMANT":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
