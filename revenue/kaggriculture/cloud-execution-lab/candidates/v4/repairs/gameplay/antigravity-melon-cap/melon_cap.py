# SPDX-License-Identifier: Apache-2.0
"""Conservative MELON production cap for the recovered R04 lane.

The original Antigravity carrier counted only MELON already sold. That is not
sufficient to cap lifetime production: held MELON and live MELON plantings are
already committed supply too. This source therefore reserves all three before
admitting any new MELON proposal.

The default cap remains 28 units as a deliberately conservative policy knob;
it is *not* claimed to equal exact full-season town consumption. Official
engine town-center consumption is handled only by the sold-count fallback.

FourthQuadrant proposals are atomic executable alternatives. This module never
partially shrinks outer proposal metadata: it authenticates the MELON PLANT
cardinality from every route variant's executable ``patches`` payload, requires
all variants and producer metadata to agree, and admits the original proposal
object only when that whole commitment fits the remaining real-world budget.

Default OFF. The runtime must not call this module unless the existing
``r04_melon_cap`` flag is exactly ``True``.
"""
from __future__ import annotations

from typing import Any

MELON_LIFETIME_UNIT_CAP = 28
MELON_UNITS_PER_PLANT = 6  # official engine CROPS['MELON']['max_yield']
TOWN_CENTER_INTERVAL = 24
MARKET_I0 = 10_000


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _plain_nonnegative_int(value: Any) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def _own_farm(observation: Any) -> dict[str, Any] | None:
    player = _plain_nonnegative_int(_get(observation, "player"))
    farms = _get(observation, "farms")
    if player is None or not isinstance(farms, (list, tuple)) or player >= len(farms):
        return None
    farm = farms[player]
    return farm if isinstance(farm, dict) else None


def _town_consumed_before_step(step: int) -> int:
    # Agent observation at step s reflects interpreter transitions for steps
    # 0..s-1. _town_consume fires at transition step % 24 == 0.
    return 0 if step == 0 else (step + TOWN_CENTER_INTERVAL - 1) // TOWN_CENTER_INTERVAL


def lifetime_melon_sold(observation: Any) -> int | None:
    """Conservative sold-unit count, or ``None`` when custody is malformed."""
    farm = _own_farm(observation)
    if farm is None:
        return None

    counters = farm.get("sale_counters")
    if isinstance(counters, dict) and "MELON" in counters:
        return _plain_nonnegative_int(counters["MELON"])

    step = _plain_nonnegative_int(_get(observation, "step"))
    market = _get(observation, "market")
    inventory = market.get("inventory") if isinstance(market, dict) else None
    inv = _plain_nonnegative_int(inventory.get("MELON")) if isinstance(inventory, dict) else None
    if step is None or inv is None:
        return None

    # MELON cannot be BUY_PRODUCT'ed and shops do not consume it. Rival sales
    # raise the same public inventory, so attributing all positive drift to us
    # is conservative for a cap.
    return max(0, inv - MARKET_I0 + _town_consumed_before_step(step))


def held_melon_units(observation: Any) -> int | None:
    """Own MELON already harvested into shed/worker inventories."""
    private = _get(observation, "private")
    if not isinstance(private, dict):
        return None
    shed = private.get("shed")
    inventories = private.get("inventories")
    if not isinstance(shed, dict) or not isinstance(inventories, list):
        return None

    shed_melon = _plain_nonnegative_int(shed.get("MELON", 0))
    if shed_melon is None:
        return None
    total = shed_melon
    for inv in inventories:
        if not isinstance(inv, dict):
            return None
        qty = _plain_nonnegative_int(inv.get("MELON", 0))
        if qty is None:
            return None
        total += qty
    return total


def planted_melon_reserve(observation: Any) -> int | None:
    """Maximum future units reserved by every live own MELON tile."""
    farm = _own_farm(observation)
    if farm is None:
        return None
    rows = farm.get("tiles")
    if not isinstance(rows, list):
        return None
    plants = 0
    for row in rows:
        if not isinstance(row, list):
            return None
        for tile in row:
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == "MELON":
                plants += 1
    return plants * MELON_UNITS_PER_PLANT


def committed_melon_units(observation: Any) -> int | None:
    """Sold + held + maximum future yield of already-planted MELON."""
    sold = lifetime_melon_sold(observation)
    held = held_melon_units(observation)
    planted = planted_melon_reserve(observation)
    if sold is None or held is None or planted is None:
        return None
    return sold + held + planted


def remaining_melon_budget(observation: Any, cap: int = MELON_LIFETIME_UNIT_CAP) -> int:
    """Uncommitted MELON units; malformed custody fails closed to zero."""
    limit = _plain_nonnegative_int(cap)
    committed = committed_melon_units(observation)
    if limit is None or committed is None:
        return 0
    return max(0, limit - committed)


def max_melon_plants(observation: Any, cap: int = MELON_LIFETIME_UNIT_CAP) -> int:
    return remaining_melon_budget(observation, cap) // MELON_UNITS_PER_PLANT


def _melon_plant_actions(row: Any) -> int | None:
    """Count executable MELON PLANT actions in one canonical route row."""
    if not isinstance(row, dict):
        return None
    actions: list[Any] = []
    if "farmer" in row:
        actions.append(row["farmer"])
    hands = row.get("hands", [])
    if not isinstance(hands, (list, tuple)):
        return None
    actions.extend(hands)

    count = 0
    for action in actions:
        if not isinstance(action, (list, tuple)):
            return None
        if action and action[0] == "PLANT":
            if len(action) < 2:
                return None
            if action[1] == "MELON":
                count += 1
    return count


def executable_melon_plants(proposal: Any) -> int | None:
    """Authenticate the atomic MELON commitment from FourthQuadrant patches.

    Canonical FourthQuadrant.install() applies ``variants[*].patches`` directly.
    Outer ``tiles``/``seed_units`` are therefore cross-checks, never authority.
    Any malformed route, route-to-route disagreement, or metadata mismatch fails
    closed so a cap cannot understate the executable proposal.
    """
    if not isinstance(proposal, dict) or proposal.get("crop") != "MELON":
        return None
    variants = proposal.get("variants")
    if not isinstance(variants, dict) or not variants:
        return None

    counts: list[int] = []
    for variant in variants.values():
        if not isinstance(variant, dict):
            return None
        patches = variant.get("patches")
        if not isinstance(patches, dict) or not patches:
            return None
        route_count = 0
        for step, row in patches.items():
            if type(step) is not int or step < 0:
                return None
            row_count = _melon_plant_actions(row)
            if row_count is None:
                return None
            route_count += row_count
        if route_count <= 0:
            return None
        counts.append(route_count)

    commitment = counts[0]
    if any(count != commitment for count in counts[1:]):
        return None

    tiles = proposal.get("tiles")
    if not isinstance(tiles, (list, tuple)) or len(tiles) != commitment:
        return None
    if "size" in proposal:
        size = _plain_nonnegative_int(proposal["size"])
        if size != commitment:
            return None
    seed_units = _plain_nonnegative_int(proposal.get("seed_units"))
    if seed_units != commitment:  # MELON has one PLANT cycle in canonical producer.
        return None
    return commitment


def filter_proposals(proposals: Any, observation: Any,
                     cap: int = MELON_LIFETIME_UNIT_CAP) -> list[Any]:
    """Keep every whole executable MELON alternative that fits the budget.

    FourthQuadrant proposals are mutually exclusive: its admission callback
    returns exactly one supplied proposal. Candidate alternatives therefore do
    not consume one another's budget. Non-MELON proposals are outside this
    repair and pass through unchanged. Oversized or malformed MELON proposals
    are skipped, never truncated.
    """
    if not isinstance(proposals, (list, tuple)):
        return []
    plants_left = max_melon_plants(observation, cap)
    out: list[Any] = []
    for proposal in proposals:
        if not isinstance(proposal, dict) or proposal.get("crop") != "MELON":
            out.append(proposal)
            continue

        commitment = executable_melon_plants(proposal)
        if commitment is None or commitment > plants_left:
            continue
        out.append(proposal)
    return out


def plants_blocked(observation: Any, planned_melon_plants: Any,
                   cap: int = MELON_LIFETIME_UNIT_CAP) -> int:
    """Number of requested new MELON tiles that exceed the remaining reserve."""
    planned = _plain_nonnegative_int(planned_melon_plants)
    if planned is None:
        return 0
    return max(0, planned - max_melon_plants(observation, cap))
