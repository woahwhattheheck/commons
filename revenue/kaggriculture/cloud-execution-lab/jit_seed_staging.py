# SPDX-License-Identifier: Apache-2.0
"""Fail-closed first-day staging for expensive route-planned seed purchases.

The compiler moves an already-planned, fully day-local BUY_SEED quantity from one
early bulk order to the market turn immediately preceding each matching PLANT.
It does not invent seed quantity, alter actor actions, touch inactive market
suffixes, or make decisions from rival/private future state.

This is an experimental route compiler, not a score claim.  A caller must still
run paired official games before enabling the resulting candidate by default.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Mapping, Sequence


DEFAULT_EXPENSIVE_CROPS = ("MELON", "STRAWBERRY")


@dataclass(frozen=True)
class _Candidate:
    route_name: Any
    day_start: int
    crop: str
    anchor_step: int
    anchor_slot: int
    quantity: int
    targets: tuple[tuple[int, int], ...]

    @property
    def signature(self) -> tuple[Any, ...]:
        return (
            self.day_start,
            self.crop,
            self.anchor_step,
            self.anchor_slot,
            self.quantity,
            self.targets,
        )


def _route_label(name: Any) -> str:
    return str(name)


def _valid_action(action: Any) -> bool:
    if not isinstance(action, Mapping):
        return False
    market = action.get("market", [])
    farmer = action.get("farmer", [])
    hands = action.get("hands", [])
    return (
        isinstance(market, list)
        and isinstance(farmer, list)
        and isinstance(hands, list)
        and all(isinstance(row, list) for row in market)
        and all(isinstance(row, list) for row in hands)
    )


def _plant_count(action: Mapping[str, Any], crop: str) -> int:
    units = [action.get("farmer", []), *action.get("hands", [])]
    return sum(
        1
        for unit in units
        if isinstance(unit, list)
        and len(unit) >= 2
        and unit[0] == "PLANT"
        and unit[1] == crop
    )


def _positive_seed_rows(
    route: Sequence[Mapping[str, Any]],
    crop: str,
    start: int,
    stop: int,
    max_orders: int,
) -> list[tuple[int, int, int]]:
    rows: list[tuple[int, int, int]] = []
    for step in range(start, stop):
        market = route[step].get("market", [])
        for slot, order in enumerate(market[:max_orders]):
            if (
                isinstance(order, list)
                and len(order) >= 3
                and order[0] == "BUY_SEED"
                and order[1] == crop
            ):
                try:
                    quantity = int(order[2])
                except (TypeError, ValueError):
                    continue
                if quantity > 0:
                    rows.append((step, slot, quantity))
    return rows


def _common_prefix(left: Sequence[Any], right: Sequence[Any]) -> int:
    common = 0
    for a, b in zip(left, right):
        if a != b:
            break
        common += 1
    return common


def _active_seed_total(
    route: Sequence[Mapping[str, Any]],
    crop: str,
    start: int,
    stop: int,
    max_orders: int,
) -> int:
    return sum(
        quantity
        for _step, _slot, quantity in _positive_seed_rows(
            route, crop, start, stop, max_orders
        )
    )


def _candidate_for(
    route_name: Any,
    route: Sequence[Mapping[str, Any]],
    crop: str,
    day_start: int,
    day_stop: int,
    max_orders: int,
) -> tuple[_Candidate | None, str | None]:
    seed_rows = _positive_seed_rows(route, crop, day_start, day_stop, max_orders)
    if not seed_rows:
        return None, None
    if len(seed_rows) != 1:
        return None, "multiple_active_seed_rows"

    anchor_step, anchor_slot, quantity = seed_rows[0]
    plants = tuple(
        (step, _plant_count(route[step], crop))
        for step in range(day_start, day_stop)
        if _plant_count(route[step], crop) > 0
    )
    if not plants:
        return None, "seed_without_same_day_plant"
    if any(step <= anchor_step for step, _quantity in plants):
        return None, "plant_not_strictly_after_anchor"
    demand = sum(count for _step, count in plants)
    if demand != quantity:
        return None, "seed_quantity_not_exact_day_demand"

    target_counts: dict[int, int] = {}
    for plant_step, count in plants:
        target = plant_step - 1
        if target < anchor_step:
            return None, "missing_preceding_market_turn"
        target_counts[target] = target_counts.get(target, 0) + count

    return (
        _Candidate(
            route_name=route_name,
            day_start=day_start,
            crop=crop,
            anchor_step=anchor_step,
            anchor_slot=anchor_slot,
            quantity=quantity,
            targets=tuple(sorted(target_counts.items())),
        ),
        None,
    )


def _place_seed_order(
    action: dict[str, Any],
    crop: str,
    quantity: int,
    max_orders: int,
) -> tuple[bool, int | None]:
    """Reserve one active slot without moving any existing nonblank row."""
    market = action["market"]
    for slot, row in enumerate(market[:max_orders]):
        if not row:
            market[slot] = ["BUY_SEED", crop, quantity]
            return True, slot
    if len(market) < max_orders:
        market.append(["BUY_SEED", crop, quantity])
        return True, len(market) - 1
    return False, None


def _apply_candidate(
    route: list[dict[str, Any]],
    candidate: _Candidate,
    max_orders: int,
    turns_per_day: int,
) -> tuple[bool, dict[str, Any]]:
    crop = candidate.crop
    anchor = route[candidate.anchor_step]
    market = anchor["market"]
    if candidate.anchor_slot >= min(len(market), max_orders):
        return False, {"reason": "anchor_left_active_prefix"}
    row = market[candidate.anchor_slot]
    if not (
        isinstance(row, list)
        and len(row) >= 3
        and row[0] == "BUY_SEED"
        and row[1] == crop
        and int(row[2]) == candidate.quantity
    ):
        return False, {"reason": "anchor_changed_before_apply"}

    targets = dict(candidate.targets)
    retained = int(targets.pop(candidate.anchor_step, 0))
    market[candidate.anchor_slot] = (
        ["BUY_SEED", crop, retained] if retained > 0 else []
    )
    placements: list[dict[str, int]] = []
    if retained:
        placements.append(
            {"step": candidate.anchor_step, "slot": candidate.anchor_slot, "quantity": retained}
        )

    for step, quantity in sorted(targets.items()):
        if step < 0 or step >= len(route):
            return False, {"reason": "target_out_of_route"}
        if step // turns_per_day != candidate.day_start // turns_per_day:
            return False, {"reason": "target_crossed_day"}
        action = route[step]
        existing = [
            slot
            for slot, order in enumerate(action["market"][:max_orders])
            if (
                isinstance(order, list)
                and len(order) >= 3
                and order[0] == "BUY_SEED"
                and order[1] == crop
                and int(order[2]) > 0
            )
        ]
        if existing:
            return False, {"reason": "target_already_has_crop_seed"}
        placed, slot = _place_seed_order(action, crop, quantity, max_orders)
        if not placed:
            return False, {"reason": "no_reserved_active_market_slot", "step": step}
        placements.append({"step": step, "slot": int(slot), "quantity": quantity})

    return True, {"reason": "staged", "placements": placements}


def _actor_surface(route: Sequence[Mapping[str, Any]]) -> list[tuple[Any, Any]]:
    return [(deepcopy(row.get("farmer")), deepcopy(row.get("hands"))) for row in route]


def _market_tail_surface(
    route: Sequence[Mapping[str, Any]], max_orders: int
) -> list[list[Any]]:
    return [deepcopy(row.get("market", [])[max_orders:]) for row in route]


def _prefix_matrix(routes: Mapping[Any, Sequence[Any]]) -> dict[tuple[Any, Any], int]:
    names = list(routes)
    return {
        (left, right): _common_prefix(routes[left], routes[right])
        for left, right in combinations(names, 2)
    }


def compile_jit_expensive_seed_routes(
    routes: Mapping[Any, Sequence[Mapping[str, Any]]],
    *,
    max_orders: int = 10,
    turns_per_day: int = 24,
    expensive_crops: Sequence[str] = DEFAULT_EXPENSIVE_CROPS,
    first_day_only: bool = True,
) -> tuple[dict[Any, list[dict[str, Any]]], dict[str, Any]]:
    """Return detached staged routes and a deterministic structural certificate.

    Certification is deliberately narrow:
    * only a single active seed row may own a crop/day;
    * its quantity must exactly equal strictly-future same-day PLANT requests;
    * every route still prefix-compatible at the anchor must expose the identical
      staging obligation;
    * every injected order reserves an already-empty or appendable active slot;
    * actor actions, inactive market suffixes, total seed quantity, and pairwise
      branch prefix lengths must remain exact.

    The default considers day zero only, where no prior-day seed carry exists in
    the standard game.  It does not model affordability or claim score uplift.
    """
    original = deepcopy(dict(routes))
    report: dict[str, Any] = {
        "changed": False,
        "certified": False,
        "reason": "no_certified_plan",
        "max_orders": max_orders,
        "turns_per_day": turns_per_day,
        "first_day_only": bool(first_day_only),
        "expensive_crops": sorted({str(crop) for crop in expensive_crops}),
        "plans": [],
        "rejections": [],
        "changed_routes": [],
        "changed_steps": {},
        "invariants": {
            "actor_surface_exact": True,
            "inactive_market_suffix_exact": True,
            "seed_quantity_exact": True,
            "branch_topology_exact": True,
        },
    }

    if not isinstance(routes, Mapping) or not routes:
        report["reason"] = "empty_or_non_mapping_routes"
        return original, report
    if isinstance(max_orders, bool) or not isinstance(max_orders, int) or max_orders <= 0:
        report["reason"] = "invalid_max_orders"
        return original, report
    if (
        isinstance(turns_per_day, bool)
        or not isinstance(turns_per_day, int)
        or turns_per_day <= 1
    ):
        report["reason"] = "invalid_turns_per_day"
        return original, report

    names = list(routes)
    for name in names:
        route = routes[name]
        if (
            not isinstance(route, Sequence)
            or isinstance(route, (str, bytes, bytearray))
            or not all(_valid_action(action) for action in route)
        ):
            report["reason"] = "malformed_route"
            report["rejections"].append(
                {"route": _route_label(name), "reason": "malformed_route"}
            )
            return original, report

    crops = tuple(sorted({str(crop) for crop in expensive_crops if str(crop)}))
    candidates: dict[tuple[Any, int, str], _Candidate] = {}
    route_lengths = {len(routes[name]) for name in names}
    if len(route_lengths) != 1:
        report["reason"] = "route_length_mismatch"
        return original, report
    route_length = next(iter(route_lengths))

    day_starts = [0] if first_day_only else list(range(0, route_length, turns_per_day))
    for name in names:
        route = routes[name]
        for day_start in day_starts:
            if day_start >= route_length:
                continue
            day_stop = min(route_length, day_start + turns_per_day)
            for crop in crops:
                candidate, rejection = _candidate_for(
                    name, route, crop, day_start, day_stop, max_orders
                )
                if candidate is not None:
                    candidates[(name, day_start, crop)] = candidate
                elif rejection is not None:
                    report["rejections"].append(
                        {
                            "route": _route_label(name),
                            "day_start": day_start,
                            "crop": crop,
                            "reason": rejection,
                        }
                    )

    original_prefixes = _prefix_matrix(routes)
    planned_groups: list[tuple[tuple[Any, ...], _Candidate]] = []
    seen: set[tuple[Any, ...]] = set()

    for key in sorted(
        candidates,
        key=lambda item: (_route_label(item[0]), item[1], item[2]),
    ):
        name, day_start, crop = key
        candidate = candidates[key]
        group = tuple(
            other
            for other in names
            if _common_prefix(routes[name], routes[other]) > candidate.anchor_step
        )
        peer_candidates = [
            candidates.get((other, day_start, crop)) for other in group
        ]
        if any(peer is None or peer.signature != candidate.signature for peer in peer_candidates):
            report["rejections"].append(
                {
                    "route": _route_label(name),
                    "day_start": day_start,
                    "crop": crop,
                    "reason": "prefix_compatible_routes_disagree",
                    "compatible_routes": sorted(_route_label(other) for other in group),
                }
            )
            continue
        group_key = (
            tuple(sorted(_route_label(other) for other in group)),
            candidate.signature,
        )
        if group_key in seen:
            continue
        seen.add(group_key)
        planned_groups.append((group, candidate))

    staged = deepcopy(original)
    accepted: list[dict[str, Any]] = []

    for group, template in sorted(
        planned_groups,
        key=lambda entry: (
            entry[1].anchor_step,
            entry[1].crop,
            tuple(sorted(_route_label(name) for name in entry[0])),
        ),
    ):
        trial = {name: deepcopy(staged[name]) for name in group}
        details: dict[Any, dict[str, Any]] = {}
        okay = True
        for name in group:
            candidate = candidates[(name, template.day_start, template.crop)]
            applied, detail = _apply_candidate(
                trial[name], candidate, max_orders, turns_per_day
            )
            if not applied:
                okay = False
                detail = dict(detail)
                detail["route"] = _route_label(name)
                report["rejections"].append(
                    {
                        "route": _route_label(name),
                        "day_start": template.day_start,
                        "crop": template.crop,
                        **detail,
                    }
                )
                break
            details[name] = detail
        if not okay:
            continue

        day_stop = min(route_length, template.day_start + turns_per_day)
        quantity_ok = all(
            _active_seed_total(
                trial[name],
                template.crop,
                template.day_start,
                day_stop,
                max_orders,
            )
            == candidates[(name, template.day_start, template.crop)].quantity
            for name in group
        )
        if not quantity_ok:
            report["rejections"].append(
                {
                    "routes": sorted(_route_label(name) for name in group),
                    "day_start": template.day_start,
                    "crop": template.crop,
                    "reason": "seed_quantity_postcondition_failed",
                }
            )
            continue

        for name in group:
            staged[name] = trial[name]
        accepted.append(
            {
                "routes": sorted(_route_label(name) for name in group),
                "day_start": template.day_start,
                "crop": template.crop,
                "anchor_step": template.anchor_step,
                "anchor_slot": template.anchor_slot,
                "quantity": template.quantity,
                "targets": [
                    {"step": step, "quantity": quantity}
                    for step, quantity in template.targets
                ],
                "placements": {
                    _route_label(name): details[name]["placements"] for name in group
                },
            }
        )

    actor_exact = all(
        _actor_surface(staged[name]) == _actor_surface(original[name]) for name in names
    )
    tail_exact = all(
        _market_tail_surface(staged[name], max_orders)
        == _market_tail_surface(original[name], max_orders)
        for name in names
    )
    branch_exact = _prefix_matrix(staged) == original_prefixes

    report["invariants"]["actor_surface_exact"] = actor_exact
    report["invariants"]["inactive_market_suffix_exact"] = tail_exact
    report["invariants"]["branch_topology_exact"] = branch_exact
    report["invariants"]["seed_quantity_exact"] = all(
        _active_seed_total(
            staged[name],
            plan["crop"],
            plan["day_start"],
            min(route_length, plan["day_start"] + turns_per_day),
            max_orders,
        )
        == plan["quantity"]
        for plan in accepted
        for name in names
        if _route_label(name) in plan["routes"]
    )

    if not all(report["invariants"].values()):
        report["reason"] = "global_postcondition_failed"
        report["plans"] = []
        return original, report

    changed_routes = [name for name in names if staged[name] != original[name]]
    changed_steps: dict[str, list[int]] = {}
    for name in changed_routes:
        changed_steps[_route_label(name)] = [
            step
            for step, (before, after) in enumerate(zip(original[name], staged[name]))
            if before != after
        ]

    report["plans"] = accepted
    report["changed_routes"] = sorted(_route_label(name) for name in changed_routes)
    report["changed_steps"] = {
        name: changed_steps[name] for name in sorted(changed_steps)
    }
    report["changed"] = bool(changed_routes)
    report["certified"] = bool(changed_routes and accepted)
    report["reason"] = "staged" if report["certified"] else "no_certified_plan"
    return staged, report
