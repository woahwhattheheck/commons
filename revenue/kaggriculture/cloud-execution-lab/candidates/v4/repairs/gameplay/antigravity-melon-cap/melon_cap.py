# SPDX-License-Identifier: Apache-2.0
"""Conservative MELON production cap for the recovered R04 lane.

The original Antigravity carrier counted only MELON already sold. That is not
sufficient to cap lifetime production: held MELON and live MELON plantings are
already committed supply too. This source therefore reserves all three before
admitting any new MELON proposal.

FourthQuadrant proposals are mutually exclusive alternatives. Their executable
work lives in ``proposal['variants'][route_id]['patches']``; outer ``tiles`` and
``seed_units`` are metadata only. MELON alternatives are therefore admitted
whole and unchanged only after every route variant authenticates the same
executable MELON PLANT cardinality. An oversized or malformed MELON alternative
is dropped; inspecting one alternative never spends budget for another.

The default cap remains 28 units as a deliberately conservative policy knob;
it is *not* claimed to equal exact full-season town consumption. Official
engine town-center consumption is handled only by the sold-count fallback.

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


def _is_melon_plant(action: Any) -> bool:
    return (isinstance(action, (list, tuple)) and len(action) >= 2
            and action[0] == "PLANT" and action[1] == "MELON")


def _variant_new_melon_plants(variant: Any, workers: int) -> int | None:
    """Count executable MELON PLANTs in FourthQuadrant-added worker slots.

    Canonical FourthQuadrant appends ``workers`` temporary workers after the
    ``incumbent_hands`` recorded in each ``worker_days`` entry. Counting only
    those slots avoids charging unrelated authored actions copied into patch
    rows while still inspecting the exact rows the consumer will execute.
    """
    if not isinstance(variant, dict) or workers <= 0:
        return None
    patches = variant.get("patches")
    worker_days = variant.get("worker_days")
    if not isinstance(patches, dict) or not isinstance(worker_days, list):
        return None

    days: dict[int, int] = {}
    for entry in worker_days:
        if not isinstance(entry, dict):
            return None
        day = _plain_nonnegative_int(entry.get("day"))
        incumbent = _plain_nonnegative_int(entry.get("incumbent_hands"))
        if day is None or incumbent is None or day in days:
            return None
        days[day] = incumbent
    if not days:
        return None

    plants = 0
    for step, row in patches.items():
        step_i = _plain_nonnegative_int(step)
        if step_i is None or not isinstance(row, dict):
            return None
        incumbent = days.get(step_i // 24)
        if incumbent is None:
            return None
        hands = row.get("hands", [])
        if not isinstance(hands, (list, tuple)):
            return None
        for action in hands[incumbent:incumbent + workers]:
            plants += int(_is_melon_plant(action))
    return plants


def executable_melon_plants(proposal: Any) -> int | None:
    """Authenticate one canonical FourthQuadrant MELON alternative.

    All route variants must execute the same positive number of newly-added
    MELON PLANT actions, and that cardinality must agree with producer metadata.
    Any mismatch fails closed rather than trusting shallow metadata.
    """
    if not isinstance(proposal, dict) or proposal.get("crop") != "MELON":
        return None
    workers = _plain_nonnegative_int(proposal.get("workers"))
    tiles = proposal.get("tiles")
    seed_units = _plain_nonnegative_int(proposal.get("seed_units"))
    variants = proposal.get("variants")
    if (workers is None or workers <= 0 or not isinstance(tiles, (list, tuple))
            or not isinstance(variants, dict) or not variants):
        return None
    expected = len(tiles)
    if expected <= 0 or seed_units != expected:
        return None

    counts = []
    for route_id, variant in variants.items():
        if not isinstance(route_id, str) or not route_id:
            return None
        count = _variant_new_melon_plants(variant, workers)
        if count is None:
            return None
        counts.append(count)
    if any(count != expected for count in counts):
        return None
    return expected


def filter_proposals(proposals: Any, observation: Any,
                     cap: int = MELON_LIFETIME_UNIT_CAP) -> list[Any]:
    """Keep complete MELON alternatives whose executable commitment fits.

    FourthQuadrant admission selects at most one supplied proposal, so candidate
    alternatives do not spend one another's budget. Objects are never shrunk:
    admitted alternatives retain identity for the consumer's membership check.
    """
    if not isinstance(proposals, (list, tuple)):
        return []
    plants_left = max_melon_plants(observation, cap)
    out: list[Any] = []
    for proposal in proposals:
        if not isinstance(proposal, dict) or proposal.get("crop") != "MELON":
            out.append(proposal)
            continue
        plants = executable_melon_plants(proposal)
        if plants is not None and plants <= plants_left:
            out.append(proposal)
    return out


def plants_blocked(observation: Any, planned_melon_plants: Any,
                   cap: int = MELON_LIFETIME_UNIT_CAP) -> int:
    """Number of requested new MELON tiles that exceed the remaining reserve."""
    planned = _plain_nonnegative_int(planned_melon_plants)
    if planned is None:
        return 0
    return max(0, planned - max_melon_plants(observation, cap))
