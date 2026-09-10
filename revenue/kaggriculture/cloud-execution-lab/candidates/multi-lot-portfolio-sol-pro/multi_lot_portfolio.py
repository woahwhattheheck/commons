# SPDX-License-Identifier: Apache-2.0
"""Fail-closed portfolio composition for independently evaluated SELL plans.

The canonical scheduler deliberately preserves all inherited market indices and
may append at most one SELL row per product.  A plan that needs to sell more of
an item than inherited SELL rows already offer therefore consumes one finite
suffix slot.  This module allocates those shared slots once, globally.

Safety rule: the canonical scalar winner is always retained.  Additional plans
are admitted only when their current-turn sale is not below the scheduler's
pre-portfolio quantity.  They therefore cannot remove receipts that an
inherited cash-dependent order relied upon.  Malformed or ambiguous inputs
raise ``PortfolioError`` so the caller can fall back to the canonical winner.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from typing import Any


class PortfolioError(ValueError):
    """The candidate set cannot be composed without guessing."""


@dataclass(frozen=True)
class PortfolioDecision:
    """Selected original candidate mappings plus an auditable allocation receipt."""

    selected: tuple[Mapping[str, Any], ...]
    skipped_decrease: tuple[str, ...]
    skipped_slots: tuple[str, ...]
    inherited_slots: int
    free_suffix_slots: int
    suffix_slots_used: int
    anchor_item: str

    def diagnostics(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "anchor_item": self.anchor_item,
            "selected_items": [str(row["item"]) for row in self.selected],
            "skipped_decrease": list(self.skipped_decrease),
            "skipped_slots": list(self.skipped_slots),
            "inherited_slots": self.inherited_slots,
            "free_suffix_slots": self.free_suffix_slots,
            "suffix_slots_used": self.suffix_slots_used,
        }


def _plain_int(value: Any, *, field: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise PortfolioError(f"{field} must be an integer >= {minimum}")
    return value


def _rank(value: Any, *, field: str) -> tuple[bool, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise PortfolioError(f"{field} must contain forced-feasibility and gain")
    forced, gain = value
    if not isinstance(forced, bool):
        raise PortfolioError(f"{field}[0] must be bool")
    if not isinstance(gain, (int, float)) or isinstance(gain, bool):
        raise PortfolioError(f"{field}[1] must be numeric")
    gain = float(gain)
    if not math.isfinite(gain):
        raise PortfolioError(f"{field}[1] must be finite")
    return forced, gain


def _current_quantity(plan: Any, *, item: str, now: int) -> int:
    if not isinstance(plan, Sequence) or isinstance(plan, (str, bytes, bytearray)):
        raise PortfolioError(f"plan for {item} must be a sequence")
    seen: set[int] = set()
    current = 0
    previous = now - 1
    for index, row in enumerate(plan):
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes, bytearray)) or len(row) != 2:
            raise PortfolioError(f"plan[{index}] for {item} must be (step, quantity)")
        step = _plain_int(row[0], field=f"plan[{index}].step")
        quantity = _plain_int(row[1], field=f"plan[{index}].quantity")
        if step < now:
            raise PortfolioError(f"plan for {item} contains a past step")
        if step in seen or step <= previous:
            raise PortfolioError(f"plan for {item} must have unique increasing steps")
        seen.add(step)
        previous = step
        if step == now:
            current = quantity
    return current


def _inherited_offers(market: Any) -> tuple[int, dict[str, int]]:
    if not isinstance(market, Sequence) or isinstance(market, (str, bytes, bytearray)):
        raise PortfolioError("market must be a sequence")
    offered: dict[str, int] = {}
    for index, raw in enumerate(market):
        if not raw:
            continue
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            raise PortfolioError(f"market[{index}] must be an order sequence")
        if raw[0] != "SELL":
            continue
        if len(raw) < 3 or not isinstance(raw[1], str) or not raw[1]:
            raise PortfolioError(f"market[{index}] has a malformed SELL identity")
        quantity = _plain_int(raw[2], field=f"market[{index}].quantity")
        offered[raw[1]] = offered.get(raw[1], 0) + quantity
    return len(market), offered


def select_portfolio(
    *,
    candidates: Sequence[Mapping[str, Any]],
    anchor_item: str,
    current: Mapping[str, Any],
    market: Sequence[Any],
    now: int,
    max_orders: int,
) -> PortfolioDecision:
    """Compose safe extra plans around the unchanged canonical scalar winner.

    Candidates are expected in the scheduler's deterministic evaluation order.
    Plans that fit inherited SELL rows consume no suffix slot.  Plans that need
    one are ranked by the existing ``(forced_feasibility, worst_gain)`` order;
    exact ties retain earlier evaluation order.
    """

    now = _plain_int(now, field="now")
    max_orders = _plain_int(max_orders, field="max_orders")
    if not isinstance(anchor_item, str) or not anchor_item:
        raise PortfolioError("anchor_item must be a nonempty string")
    if not isinstance(current, Mapping):
        raise PortfolioError("current must be a mapping")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes, bytearray)):
        raise PortfolioError("candidates must be a sequence")

    inherited_slots, offered = _inherited_offers(market)
    if inherited_slots > max_orders:
        raise PortfolioError("inherited market already exceeds max_orders")
    free_slots = max_orders - inherited_slots

    normalized: list[dict[str, Any]] = []
    seen_items: set[str] = set()
    for position, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping):
            raise PortfolioError(f"candidate[{position}] must be a mapping")
        item = candidate.get("item")
        if not isinstance(item, str) or not item:
            raise PortfolioError(f"candidate[{position}].item must be nonempty")
        if item in seen_items:
            raise PortfolioError(f"duplicate candidate item: {item}")
        seen_items.add(item)
        if item not in current:
            raise PortfolioError(f"current quantity missing for {item}")
        baseline = _plain_int(current[item], field=f"current[{item}]")
        quantity = _current_quantity(candidate.get("plan"), item=item, now=now)
        rank = _rank(candidate.get("rank"), field=f"candidate[{position}].rank")
        normalized.append({
            "source": candidate,
            "item": item,
            "position": position,
            "baseline": baseline,
            "quantity": quantity,
            "rank": rank,
            "slot_need": int(quantity > offered.get(item, 0)),
        })

    anchors = [row for row in normalized if row["item"] == anchor_item]
    if len(anchors) != 1:
        raise PortfolioError("anchor_item must identify exactly one candidate")
    anchor = anchors[0]
    if anchor["slot_need"] > free_slots:
        raise PortfolioError("canonical anchor cannot fit the available suffix slots")

    selected_positions = {int(anchor["position"])}
    used_slots = int(anchor["slot_need"])
    skipped_decrease: list[str] = []
    slot_claimants: list[dict[str, Any]] = []

    for row in normalized:
        if row is anchor:
            continue
        if row["quantity"] < row["baseline"]:
            skipped_decrease.append(str(row["item"]))
            continue
        if not row["slot_need"]:
            selected_positions.add(int(row["position"]))
            continue
        slot_claimants.append(row)

    # Highest existing scheduler rank wins scarce suffix capacity.  The negative
    # position term preserves earlier deterministic evaluation order on ties.
    slot_claimants.sort(
        key=lambda row: (int(row["rank"][0]), float(row["rank"][1]), -int(row["position"])),
        reverse=True,
    )
    skipped_slots: list[str] = []
    remaining_slots = free_slots - used_slots
    for row in slot_claimants:
        if remaining_slots > 0:
            selected_positions.add(int(row["position"]))
            remaining_slots -= 1
            used_slots += 1
        else:
            skipped_slots.append(str(row["item"]))

    selected = tuple(
        row["source"] for row in normalized if int(row["position"]) in selected_positions
    )
    return PortfolioDecision(
        selected=selected,
        skipped_decrease=tuple(skipped_decrease),
        skipped_slots=tuple(skipped_slots),
        inherited_slots=inherited_slots,
        free_suffix_slots=free_slots,
        suffix_slots_used=used_slots,
        anchor_item=anchor_item,
    )
