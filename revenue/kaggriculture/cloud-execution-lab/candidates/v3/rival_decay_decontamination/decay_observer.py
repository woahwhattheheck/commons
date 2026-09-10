# SPDX-License-Identifier: Apache-2.0
"""Executable rival-harvest ledger with exact public false-supply subtraction.

The current SELL observer treats every public rival ``yield_units`` decline as a
harvested lot. The pinned interpreter also decrements expired plant yield by one
on deterministic lifespan-parity ticks. In addition, HARVEST is a single unit
action on the unit's current tile: when no rival actor occupied a coordinate in
the predecessor observation, a decline there cannot be a harvest. This module
removes only those publicly provable false units and preserves ambiguous input.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

OPERATION = "titan-v3-rival-decay-decontamination-20260910-01"
REACHABILITY_OPERATION = (
    "titan-v3-rival-harvest-actor-reachability-closure-20260910-01"
)


def _integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _exact_coordinate(value: Any) -> tuple[int, int] | None:
    """Return a JSON actor coordinate, rejecting coercions and booleans."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    if len(value) != 2:
        return None
    x, y = value
    if isinstance(x, bool) or isinstance(y, bool):
        return None
    if not isinstance(x, int) or not isinstance(y, int):
        return None
    return x, y


def actor_occupancy_at(farm: Any, x: int, y: int) -> bool | None:
    """Prove whether a predecessor farm had any unit on ``(x, y)``.

    ``False`` is returned only from a complete, source-shaped public farm. Any
    malformed or incomplete actor/grid representation returns ``None`` so the
    caller preserves incumbent classification rather than suppressing supply.
    The official interpreter gives each listed actor one action; HARVEST does
    not move it. Therefore a contiguous decline with a proven ``False`` result
    cannot have been caused by HARVEST in that transition.
    """
    if not isinstance(farm, Mapping):
        return None
    tiles = farm.get("tiles")
    hands = farm.get("hands")
    if not isinstance(tiles, list) or not tiles:
        return None
    if not all(isinstance(row, list) and row for row in tiles):
        return None
    if not isinstance(hands, list):
        return None

    target = (x, y)
    occupied = False
    for raw in (farm.get("farmer"), *hands):
        coordinate = _exact_coordinate(raw)
        if coordinate is None:
            return None
        px, py = coordinate
        if py < 0 or py >= len(tiles):
            return None
        row = tiles[py]
        if px < 0 or px >= len(row):
            return None
        if coordinate == target:
            occupied = True
    return occupied


def is_exact_age_decay(before: Any, after: Any, transition_step: Any) -> bool:
    """Return true only for the interpreter's observable one-unit age decay.

    This deliberately requires the plant to survive as the same public object.
    Plant disappearance/WEED conversion, larger drops, replacements, animals,
    malformed values, pre-lifespan steps and wrong parity stay classified by the
    incumbent observer unless actor reachability independently proves that a
    contiguous decline could not be a harvest.
    """
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        return False
    if before.get("kind") != "PLANT" or after.get("kind") != "PLANT":
        return False
    for field in ("crop", "planted_day", "max_lifespan_step"):
        if before.get(field) != after.get(field):
            return False

    old_yield = _integer(before.get("yield_units"))
    new_yield = _integer(after.get("yield_units"))
    lifespan = _integer(before.get("max_lifespan_step"))
    step = _integer(transition_step)
    if None in (old_yield, new_yield, lifespan, step):
        return False
    assert old_yield is not None
    assert new_yield is not None
    assert lifespan is not None
    assert step is not None
    return (
        old_yield > 1
        and new_yield == old_yield - 1
        and lifespan >= 0
        and step >= lifespan
        and (step - lifespan) % 2 == 0
    )


def _product(tile: Mapping[str, Any], animals: Mapping[str, Mapping[str, Any]]) -> Any:
    if tile.get("kind") == "PLANT":
        return tile.get("crop")
    return animals.get(tile.get("animal"), {}).get("product")


def make_decay_safe_frozen_selected(
    base: type,
    *,
    products: Iterable[str],
    animals: Mapping[str, Mapping[str, Any]],
) -> type:
    """Create the executable consumer with two exact public ledger repairs.

    The method body intentionally mirrors ``SellScheduler.observe``. Its only
    semantic differences are:

    * suppress a contiguous decline when a complete predecessor farm proves no
      rival actor occupied that tile; and
    * subtract one surviving-plant unit when the transition is exact age decay.

    Uncertain continuity, actor positions or grids retain incumbent behavior.
    """
    product_set = frozenset(products)
    animal_table = {name: dict(data) for name, data in animals.items()}
    inherited_observe = base.observe

    class DecaySafeFrozenSelected(base):
        _titan_rival_decay_decontamination = OPERATION
        _titan_rival_harvest_actor_reachability = REACHABILITY_OPERATION
        _titan_predecessor_observe = inherited_observe

        def observe(self, obs):
            now = int(obs["step"])
            if self.previous is not None:
                previous_step = _integer(self.previous.get("step"))
                contiguous = previous_step == now - 1
                rival_index = 1 - int(obs["player"])
                rival_farm = self.previous["farms"][rival_index]
                old = rival_farm["tiles"]
                new = obs["farms"][rival_index]["tiles"]
                for y, row in enumerate(old):
                    for x, tile in enumerate(row):
                        if not isinstance(tile, dict):
                            continue
                        product = _product(tile, animal_table)
                        if product not in product_set:
                            continue
                        later = new[y][x]
                        before_units = max(0, int(tile.get("yield_units", 0)))
                        after_units = (
                            max(0, int(later.get("yield_units", 0)))
                            if isinstance(later, dict)
                            else 0
                        )
                        if before_units > after_units:
                            occupancy = (
                                actor_occupancy_at(rival_farm, x, y)
                                if contiguous
                                else None
                            )
                            if occupancy is False:
                                # A unit cannot move and HARVEST in its one action.
                                # This public decline is impossible harvest supply.
                                continue
                            decline = before_units - after_units
                            if contiguous and is_exact_age_decay(tile, later, now - 1):
                                decline -= 1
                            if decline > 0:
                                self.observed_harvests.setdefault(product, []).append(
                                    (now, decline)
                                )
            for product in self.observed_harvests:
                self.observed_harvests[product] = [
                    (step, quantity)
                    for step, quantity in self.observed_harvests[product]
                    if now - step <= 8
                ]

    DecaySafeFrozenSelected.__name__ = "DecaySafeFrozenSelected"
    DecaySafeFrozenSelected.__qualname__ = "DecaySafeFrozenSelected"
    DecaySafeFrozenSelected.__module__ = __name__
    return DecaySafeFrozenSelected
