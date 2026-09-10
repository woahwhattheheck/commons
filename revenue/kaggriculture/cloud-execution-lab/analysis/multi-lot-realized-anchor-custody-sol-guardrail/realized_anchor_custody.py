# SPDX-License-Identifier: Apache-2.0
"""Realized suffix-slot custody for multi-product SELL portfolios.

The rejected multi-lot experiment allocated suffix slots only among optimizer
candidates, while the unchanged scheduler renderer also emitted positive
baseline targets.  This module models that exact renderer boundary and admits
extras only when the scalar anchor remains realized.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from typing import Any


class CustodyError(ValueError):
    """Inputs are malformed or the scalar anchor cannot be proved realized."""


@dataclass(frozen=True)
class Candidate:
    source: Mapping[str, Any]
    item: str
    position: int
    quantity: int
    baseline: int
    rank: tuple[bool, float]


@dataclass(frozen=True)
class CustodyDecision:
    """Selected candidates and the exact suffix rows they realize."""

    selected: tuple[Mapping[str, Any], ...]
    rejected_decrease: tuple[str, ...]
    rejected_unrealized: tuple[str, ...]
    rejected_scalar_displacement: tuple[str, ...]
    scalar_suffix: tuple[tuple[str, int], ...]
    portfolio_suffix: tuple[tuple[str, int], ...]
    anchor_item: str
    anchor_quantity: int
    free_suffix_slots: int

    def diagnostics(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "anchor_item": self.anchor_item,
            "anchor_quantity": self.anchor_quantity,
            "selected_items": [str(row["item"]) for row in self.selected],
            "rejected_decrease": list(self.rejected_decrease),
            "rejected_unrealized": list(self.rejected_unrealized),
            "rejected_scalar_displacement": list(self.rejected_scalar_displacement),
            "scalar_suffix": [list(row) for row in self.scalar_suffix],
            "portfolio_suffix": [list(row) for row in self.portfolio_suffix],
            "free_suffix_slots": self.free_suffix_slots,
        }


def _plain_int(value: Any, *, field: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise CustodyError(f"{field} must be an integer >= {minimum}")
    return value


def _quantity_at(plan: Any, *, item: str, now: int) -> int:
    if not isinstance(plan, Sequence) or isinstance(plan, (str, bytes, bytearray)):
        raise CustodyError(f"plan for {item} must be a sequence")
    quantity = 0
    previous = now - 1
    for index, row in enumerate(plan):
        if (
            not isinstance(row, Sequence)
            or isinstance(row, (str, bytes, bytearray))
            or len(row) != 2
        ):
            raise CustodyError(f"plan[{index}] for {item} must be (step, quantity)")
        step = _plain_int(row[0], field=f"plan[{index}].step")
        amount = _plain_int(row[1], field=f"plan[{index}].quantity")
        if step < now or step <= previous:
            raise CustodyError(f"plan for {item} must have unique increasing non-past steps")
        previous = step
        if step == now:
            quantity = amount
    return quantity


def _rank(value: Any, *, field: str) -> tuple[bool, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise CustodyError(f"{field} must be (forced_feasibility, gain)")
    forced, gain = value
    if not isinstance(forced, bool):
        raise CustodyError(f"{field}[0] must be bool")
    if not isinstance(gain, (int, float)) or isinstance(gain, bool):
        raise CustodyError(f"{field}[1] must be numeric")
    numeric = float(gain)
    if not math.isfinite(numeric):
        raise CustodyError(f"{field}[1] must be finite")
    return forced, numeric


def _offers_and_slots(market: Any, *, max_orders: int) -> tuple[dict[str, int], int]:
    if not isinstance(market, Sequence) or isinstance(market, (str, bytes, bytearray)):
        raise CustodyError("market must be a sequence")
    if len(market) > max_orders:
        raise CustodyError("inherited market exceeds max_orders")
    offered: dict[str, int] = {}
    for index, raw in enumerate(market):
        if not raw:
            continue
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            raise CustodyError(f"market[{index}] must be an order sequence")
        if raw[0] != "SELL":
            continue
        if len(raw) < 3 or not isinstance(raw[1], str) or not raw[1]:
            raise CustodyError(f"market[{index}] has malformed SELL identity")
        amount = _plain_int(raw[2], field=f"market[{index}].quantity")
        offered[raw[1]] = offered.get(raw[1], 0) + amount
    return offered, max_orders - len(market)


def render_suffix(
    *,
    quantities: Mapping[str, int],
    offered: Mapping[str, int],
    available: Mapping[str, int],
    free_slots: int,
) -> tuple[tuple[str, int], ...]:
    """Reproduce the scheduler's sorted-target suffix allocation exactly.

    The bound renderer clips inherited and suffix SELL quantities to the
    pre-render ``available`` shed map.  Omitting that map was a second reason
    the rejected allocator could claim a plan was selected without proving its
    returned action contained the sale.
    """
    free_slots = _plain_int(free_slots, field="free_slots")
    if not isinstance(quantities, Mapping):
        raise CustodyError("quantities must be a mapping")
    if not isinstance(offered, Mapping):
        raise CustodyError("offered must be a mapping")
    if not isinstance(available, Mapping):
        raise CustodyError("available must be a mapping")
    rows: list[tuple[str, int]] = []
    for item in sorted(quantities):
        if not isinstance(item, str) or not item:
            raise CustodyError("quantity keys must be nonempty strings")
        quantity = _plain_int(quantities[item], field=f"quantities[{item}]")
        capacity = _plain_int(available.get(item, 0), field=f"available[{item}]")
        inherited = min(
            quantity,
            _plain_int(offered.get(item, 0), field=f"offered[{item}]"),
            capacity,
        )
        residual = min(quantity - inherited, capacity - inherited)
        if residual and len(rows) < free_slots:
            rows.append((item, residual))
    return tuple(rows)


def _preserves_scalar_suffix(
    scalar: Sequence[tuple[str, int]], tentative: Sequence[tuple[str, int]]
) -> bool:
    """Keep every scalar suffix row at its exact relative index, nondecreased."""
    if len(tentative) < len(scalar):
        return False
    return all(
        tentative[index][0] == item and tentative[index][1] >= amount
        for index, (item, amount) in enumerate(scalar)
    )


def _realized_total(
    item: str,
    *,
    quantities: Mapping[str, int],
    offered: Mapping[str, int],
    available: Mapping[str, int],
    suffix: Sequence[tuple[str, int]],
) -> int:
    requested = _plain_int(quantities.get(item, 0), field=f"quantities[{item}]")
    capacity = _plain_int(available.get(item, 0), field=f"available[{item}]")
    inherited = min(
        requested,
        _plain_int(offered.get(item, 0), field=f"offered[{item}]"),
        capacity,
    )
    appended = sum(amount for name, amount in suffix if name == item)
    return inherited + appended


def select_with_realized_anchor_custody(
    *,
    candidates: Sequence[Mapping[str, Any]],
    anchor_item: str,
    current: Mapping[str, Any],
    available: Mapping[str, Any],
    market: Sequence[Any],
    now: int,
    max_orders: int,
) -> CustodyDecision:
    """Admit extras only when the scalar rendered suffix stays in custody.

    The scalar control is the full baseline ``current`` map with only the anchor
    replaced by its candidate quantity.  Extras are considered in the rejected
    experiment's rank order.  Every tentative portfolio is passed through the
    exact sorted-target suffix renderer, including its pre-render shed-capacity
    clipping. Every scalar suffix row must remain at the same relative index
    with a nondecreased quantity, and the anchor must remain fully realized.
    Baseline claimants are therefore counted even when
    they were not optimizer candidates.
    """
    now = _plain_int(now, field="now")
    max_orders = _plain_int(max_orders, field="max_orders")
    if not isinstance(anchor_item, str) or not anchor_item:
        raise CustodyError("anchor_item must be a nonempty string")
    if not isinstance(current, Mapping):
        raise CustodyError("current must be a mapping")
    if not isinstance(candidates, Sequence) or isinstance(
        candidates, (str, bytes, bytearray)
    ):
        raise CustodyError("candidates must be a sequence")

    baseline: dict[str, int] = {}
    for item, raw in current.items():
        if not isinstance(item, str) or not item:
            raise CustodyError("current keys must be nonempty strings")
        baseline[item] = _plain_int(raw, field=f"current[{item}]")
    if not isinstance(available, Mapping):
        raise CustodyError("available must be a mapping")
    capacity: dict[str, int] = {}
    for item, raw in available.items():
        if not isinstance(item, str) or not item:
            raise CustodyError("available keys must be nonempty strings")
        capacity[item] = _plain_int(raw, field=f"available[{item}]")

    offered, free_slots = _offers_and_slots(market, max_orders=max_orders)
    normalized: list[Candidate] = []
    seen: set[str] = set()
    for position, row in enumerate(candidates):
        if not isinstance(row, Mapping):
            raise CustodyError(f"candidate[{position}] must be a mapping")
        item = row.get("item")
        if not isinstance(item, str) or not item:
            raise CustodyError(f"candidate[{position}].item must be nonempty")
        if item in seen:
            raise CustodyError(f"duplicate candidate item: {item}")
        if item not in baseline:
            raise CustodyError(f"current quantity missing for {item}")
        seen.add(item)
        normalized.append(
            Candidate(
                source=row,
                item=item,
                position=position,
                quantity=_quantity_at(row.get("plan"), item=item, now=now),
                baseline=baseline[item],
                rank=_rank(row.get("rank"), field=f"candidate[{position}].rank"),
            )
        )

    anchors = [row for row in normalized if row.item == anchor_item]
    if len(anchors) != 1:
        raise CustodyError("anchor_item must identify exactly one candidate")
    anchor = anchors[0]

    scalar_quantities = dict(baseline)
    scalar_quantities[anchor.item] = anchor.quantity
    scalar_suffix = render_suffix(
        quantities=scalar_quantities,
        offered=offered,
        available=capacity,
        free_slots=free_slots,
    )
    anchor_realized = _realized_total(
        anchor.item,
        quantities=scalar_quantities,
        offered=offered,
        available=capacity,
        suffix=scalar_suffix,
    )
    if anchor_realized != anchor.quantity:
        raise CustodyError("scalar anchor is not fully realized by the bound renderer")

    selected: list[Candidate] = [anchor]
    quantities = dict(scalar_quantities)
    rejected_decrease: list[str] = []
    rejected_unrealized: list[str] = []
    rejected_displacement: list[str] = []

    extras = [row for row in normalized if row is not anchor]
    extras.sort(
        key=lambda row: (int(row.rank[0]), row.rank[1], -row.position),
        reverse=True,
    )
    for extra in extras:
        if extra.quantity < extra.baseline:
            rejected_decrease.append(extra.item)
            continue
        tentative = dict(quantities)
        tentative[extra.item] = extra.quantity
        suffix = render_suffix(
            quantities=tentative,
            offered=offered,
            available=capacity,
            free_slots=free_slots,
        )
        tentative_selected = [*selected, extra]
        all_selected_realized = all(
            _realized_total(
                row.item,
                quantities=tentative,
                offered=offered,
                available=capacity,
                suffix=suffix,
            )
            == row.quantity
            for row in tentative_selected
        )
        if not all_selected_realized:
            rejected_unrealized.append(extra.item)
            continue
        if not _preserves_scalar_suffix(scalar_suffix, suffix):
            rejected_displacement.append(extra.item)
            continue
        quantities = tentative
        selected.append(extra)

    selected_positions = {row.position for row in selected}
    selected_sources = tuple(
        row.source for row in normalized if row.position in selected_positions
    )
    final_suffix = render_suffix(
        quantities=quantities,
        offered=offered,
        available=capacity,
        free_slots=free_slots,
    )
    return CustodyDecision(
        selected=selected_sources,
        rejected_decrease=tuple(rejected_decrease),
        rejected_unrealized=tuple(rejected_unrealized),
        rejected_scalar_displacement=tuple(rejected_displacement),
        scalar_suffix=scalar_suffix,
        portfolio_suffix=final_suffix,
        anchor_item=anchor.item,
        anchor_quantity=anchor.quantity,
        free_suffix_slots=free_slots,
    )
