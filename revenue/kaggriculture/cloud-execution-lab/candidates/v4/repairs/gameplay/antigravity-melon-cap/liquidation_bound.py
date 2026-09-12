# SPDX-License-Identifier: Apache-2.0
"""Certified realization-bound admission for Antigravity MELON proposals.

This is a successor admission surface for the recovered ``r04_melon_cap`` lane.
The historical fixed 28-unit lifetime cap is intentionally *not* used here.
A caller must instead provide an exact certificate for the number of MELON units
that the selected current route can still realize from the current observation
through terminal play (for example by legal SELL/town-consumption custody).

The certificate is a proof input, not a forecast.  Missing, malformed, or
negative proof leaves the proposal batch exactly unchanged.  When proof is
valid, already-held MELON plus the maximum remaining yield of every live MELON
plant consumes the certificate before any new planting is admitted.

Default OFF / source-only.  This module creates no feature key and does not
authorize runtime activation.
"""
from __future__ import annotations

from typing import Any

import melon_cap as legacy

MELON_UNITS_PER_PLANT = legacy.MELON_UNITS_PER_PLANT


def _plain_nonnegative_int(value: Any) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def outstanding_melon_units(observation: Any) -> int | None:
    """Unsold own MELON already held or still committed on live plants."""
    held = legacy.held_melon_units(observation)
    planted = legacy.planted_melon_reserve(observation)
    if held is None or planted is None:
        return None
    return held + planted


def remaining_realization_budget(
    observation: Any,
    certified_remaining_realization_units: Any,
) -> int | None:
    """Units available to *new* production, or ``None`` without exact proof."""
    certified = _plain_nonnegative_int(certified_remaining_realization_units)
    outstanding = outstanding_melon_units(observation)
    if certified is None or outstanding is None:
        return None
    return max(0, certified - outstanding)


def max_new_melon_plants(
    observation: Any,
    certified_remaining_realization_units: Any,
) -> int | None:
    budget = remaining_realization_budget(
        observation, certified_remaining_realization_units
    )
    if budget is None:
        return None
    return budget // MELON_UNITS_PER_PLANT


def _proposal_shape(proposal: dict[str, Any]) -> tuple[int, list[Any] | None, int | None] | None:
    """Return exact (plant count, tiles copy, seed-units-per-plant) or fail."""
    tiles_value = proposal.get("tiles")
    tiles: list[Any] | None = None
    size_from_tiles: int | None = None
    if tiles_value is not None:
        if not isinstance(tiles_value, (list, tuple)):
            return None
        tiles = list(tiles_value)
        size_from_tiles = len(tiles)

    explicit_size = proposal.get("size")
    if explicit_size is not None:
        explicit_size = _plain_nonnegative_int(explicit_size)
        if explicit_size is None:
            return None

    if size_from_tiles is None and explicit_size is None:
        return None
    if size_from_tiles is not None and explicit_size is not None and size_from_tiles != explicit_size:
        return None

    size = size_from_tiles if size_from_tiles is not None else explicit_size
    assert size is not None
    if size <= 0:
        return None

    seed_per_plant: int | None = None
    if "seed_units" in proposal:
        seed_units = _plain_nonnegative_int(proposal.get("seed_units"))
        if seed_units is None or seed_units % size:
            return None
        seed_per_plant = seed_units // size
    return size, tiles, seed_per_plant


def filter_proposals_with_realization_bound(
    proposals: Any,
    observation: Any,
    certified_remaining_realization_units: Any,
):
    """Trim aggregate MELON proposals only when a complete realization proof exists.

    Proof failure is deliberately an exact no-op: the original ``proposals``
    object is returned, rather than interpreting uncertainty as a fixed cap.
    """
    if not isinstance(proposals, (list, tuple)):
        return proposals

    plants_left = max_new_melon_plants(
        observation, certified_remaining_realization_units
    )
    if plants_left is None:
        return proposals

    parsed: list[tuple[int, list[Any] | None, int | None] | None] = []
    for proposal in proposals:
        if isinstance(proposal, dict) and proposal.get("crop") == "MELON":
            shape = _proposal_shape(proposal)
            if shape is None:
                return proposals
            parsed.append(shape)
        else:
            parsed.append(None)

    out: list[Any] = []
    changed = False
    for proposal, shape in zip(proposals, parsed):
        if shape is None:
            out.append(proposal)
            continue

        size, tiles, seed_per_plant = shape
        allowed = min(size, plants_left)
        plants_left -= allowed

        if allowed == size:
            out.append(proposal)
            continue

        changed = True
        if allowed == 0:
            continue

        shrunk = dict(proposal)
        if tiles is not None:
            shrunk["tiles"] = tiles[:allowed]
        if "size" in shrunk:
            shrunk["size"] = allowed
        if seed_per_plant is not None:
            shrunk["seed_units"] = seed_per_plant * allowed
        out.append(shrunk)

    return out if changed else proposals
