# SPDX-License-Identifier: Apache-2.0
"""Certified realization-bound admission for Antigravity MELON proposals.

This is a successor admission surface for the recovered ``r04_melon_cap`` lane.
The historical fixed 28-unit lifetime cap is intentionally *not* used here.
A caller must instead provide an exact certificate for the number of MELON units
that the selected current route can still realize from the current observation
through terminal play (for example by legal SELL/town-consumption custody).

The certificate is a proof input, not a forecast. Missing, malformed, or
negative proof leaves the proposal batch exactly unchanged. When proof is
valid, already-held MELON plus the maximum remaining yield of every live MELON
plant consumes the certificate before any new planting is admitted.

FourthQuadrant proposal entries are mutually exclusive alternatives. Each MELON
alternative is therefore authenticated independently from its executable
``variants[*].patches`` program using the canonical legacy source helper and is
kept as the exact original object only when its whole commitment fits the
remaining realization certificate. Alternatives are never shallow-shrunk and
inspecting one option never spends capacity for another.

Default OFF / source-only. This module creates no feature key and does not
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


def filter_proposals_with_realization_bound(
    proposals: Any,
    observation: Any,
    certified_remaining_realization_units: Any,
):
    """Keep whole executable MELON alternatives that individually fit proof.

    Certificate/custody failure remains an exact no-op because the caller has
    not supplied enough proof to replace the legacy policy. With a valid proof,
    malformed or oversized MELON alternatives fail closed individually while
    unrelated alternatives retain value, order, and object identity.
    """
    if not isinstance(proposals, (list, tuple)):
        return proposals

    plants_left = max_new_melon_plants(
        observation, certified_remaining_realization_units
    )
    if plants_left is None:
        return proposals

    out: list[Any] = []
    changed = False
    for proposal in proposals:
        if not isinstance(proposal, dict) or proposal.get("crop") != "MELON":
            out.append(proposal)
            continue

        plants = legacy.executable_melon_plants(proposal)
        if plants is not None and plants <= plants_left:
            out.append(proposal)
            continue

        changed = True

    return out if changed else proposals
