from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

CONSUMABLE_BY_ACTION = {
    "FEED": "WHEAT",
    "FERTILIZE": "FERTILIZER",
}
PREFERRED_ITEMS = ("WHEAT", "FERTILIZER")


@dataclass(frozen=True)
class CarrybankDecision:
    """A fail-closed same-day inventory-hoist decision."""

    item: str
    quantity: int
    pressure_units: int
    guaranteed_consumption_units: int

    def action(self) -> list[object]:
        return ["PICKUP", self.item, self.quantity]


def _op(action: object) -> str:
    if isinstance(action, (list, tuple)) and action:
        return str(action[0]).upper()
    return ""


def _future_consumption(
    future_unit_actions: Sequence[object],
    turns_remaining: int,
) -> dict[str, int]:
    """Count same-day carried-inventory sinks in the supplied actor continuation."""
    remaining = max(0, int(turns_remaining))
    counts = {item: 0 for item in PREFERRED_ITEMS}
    for action in future_unit_actions[:remaining]:
        item = CONSUMABLE_BY_ACTION.get(_op(action))
        if item is not None:
            counts[item] += 1
    return counts


def admit_carrybank_pickup(
    *,
    current_unit_action: object,
    adjacent_to_shed: bool,
    shed: Mapping[str, int],
    shed_capacity: int,
    projected_shed_inflow_units: int,
    current_inventory: Mapping[str, int],
    future_unit_actions: Sequence[object],
    turns_remaining: int,
) -> CarrybankDecision | None:
    """
    Admit a proactive PICKUP only when it is capacity-useful and same-day-consumable.

    This helper is deliberately narrow:
      * it may replace only a current PASS, never productive work;
      * the actor must already be adjacent to SHED;
      * only WHEAT/FERTILIZER qualify because FEED/FERTILIZE are carried-item sinks;
      * pickup quantity is capped by projected shed-capacity pressure;
      * pickup quantity is capped by *additional* same-day planned consumption after
        accounting for inventory the actor already carries.

    The official engine silently destroys DROP overflow and discards carried overflow
    at end-of-day shed return. Therefore this helper never relies on DROP or EOD return
    to make a hoist safe.
    """
    if _op(current_unit_action) != "PASS":
        return None
    if not adjacent_to_shed:
        return None

    capacity = max(0, int(shed_capacity))
    used = sum(max(0, int(v)) for v in shed.values())
    room = max(0, capacity - used)
    pressure = max(0, int(projected_shed_inflow_units) - room)
    if pressure <= 0:
        return None

    consumption = _future_consumption(future_unit_actions, turns_remaining)
    candidates: list[tuple[int, int, str]] = []
    for priority, item in enumerate(PREFERRED_ITEMS):
        available = max(0, int(shed.get(item, 0)))
        carried = max(0, int(current_inventory.get(item, 0)))
        additional_sink = max(0, consumption[item] - carried)
        quantity = min(pressure, available, additional_sink)
        if quantity > 0:
            # Prefer the decision freeing the most capacity; stable priority breaks ties.
            candidates.append((quantity, -priority, item))

    if not candidates:
        return None

    quantity, _neg_priority, item = max(candidates)
    return CarrybankDecision(
        item=item,
        quantity=quantity,
        pressure_units=pressure,
        guaranteed_consumption_units=consumption[item],
    )
