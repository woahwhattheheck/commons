# SPDX-License-Identifier: Apache-2.0
"""Current-ABI semantic port of TITAN V3.1 row-shed SELL ordering.

This is an additive component for the single canonical V4 tree.  It deliberately
imports no legacy router/materializer and owns no feature/default.  A composer
may apply :func:`transform_selected` at the selected-action boundary after the
unit projection has produced the exact post-unit shed.

Historical donor: commons@7cbe552087626d09dbd8a84be8fa89efc7320ad0
  candidates/v3/overlay/r04_full_router.py

Reviewed semantics retained:
* consider only the leading contiguous SELL block;
* a falsey/raw slot is a hard barrier and all tail indices remain where they are;
* rank rows by the price drop caused by the units they can actually sell,
  min(requested quantity, post-unit shed stock);
* if shed evidence for any leading row is incomplete/type-poisoned, rank the
  whole block by requested quantity (the incumbent ROW_ORDER fallback);
* if a requested quantity is not a plain non-negative int, preserve the exact
  parent ordering;
* stable ties keep incumbent relative order;
* malformed current-ABI envelopes fail closed to the exact parent action.

The component changes row order only.  It never changes a row, quantity, slot
count, tail row, unit action, market inventory, or shed value.
"""
from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from typing import Any

DONOR_COMMIT = "7cbe552087626d09dbd8a84be8fa89efc7320ad0"
DONOR_SOURCE_SHA256 = "569b515c89f56a8f060ce94de218a341ae0e5b3c8e0e2c6428a8a0f08a462b05"
DONOR_TEST_SHA256 = "b8f81248e37078d15e767f2883c59589a670353c248c5d5eab126b58f41cabee"
DEFAULT_INVENTORY = 10_000

PriceFn = Callable[[str, int], int]


def _plain_nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _leading_sell_count(market: list[Any]) -> int:
    lead = 0
    while lead < len(market):
        row = market[lead]
        if not row or not isinstance(row, list) or not row or row[0] != "SELL":
            break
        lead += 1
    return lead


def order_leading_sells(
    market: list[Any],
    inventory: Mapping[str, Any],
    shed: Mapping[str, Any] | None,
    *,
    price_at: PriceFn,
    priced_items: Collection[str],
) -> list[Any]:
    """Return row-shed ordering while preserving every row object and tail slot.

    This function mirrors the reviewed donor's ``order_sells`` contract.  The
    caller is responsible for supplying the standard-market quote function.
    ``market`` itself is never mutated.
    """
    lead = _leading_sell_count(market)
    if lead < 2:
        return market

    block = market[:lead]
    if any(len(row) < 3 or not _plain_nonnegative_int(row[2]) for row in block):
        return market

    effective_shed: Mapping[str, Any] | None = shed
    if effective_shed is not None:
        if not isinstance(effective_shed, Mapping) or any(
            not _plain_nonnegative_int(effective_shed.get(row[1])) for row in block
        ):
            # Exact donor behavior: incomplete/poisoned projection disables shed
            # pricing for the entire leading block, rather than mixing modes.
            effective_shed = None

    priced = frozenset(priced_items)

    def drop(row: list[Any]) -> int:
        item = row[1] if len(row) > 1 else None
        if item not in priced or len(row) < 3:
            return 0
        level = int(inventory.get(item, DEFAULT_INVENTORY))
        quantity = row[2]
        if effective_shed is not None:
            quantity = min(quantity, effective_shed[item])
        before = int(price_at(item, level))
        after = int(price_at(item, level + quantity))
        return (before - after) * quantity

    # sorted() is stable, matching the donor's tie behavior.
    return sorted(block, key=drop, reverse=True) + market[lead:]


def transform_selected(
    selected_action: Any,
    observation: Any,
    post_unit_shed: Any,
    *,
    price_at: PriceFn,
    priced_items: Collection[str],
) -> Any:
    """Apply row-shed at the current selected-action/post-unit boundary.

    Failure and no-op paths return *the exact input object*, which makes this safe
    to stage behind a caller-owned admission seam.  A successful reorder returns
    one shallow action copy with a newly ordered market list; individual rows are
    preserved by identity and are never edited.
    """
    try:
        if not isinstance(selected_action, dict) or not isinstance(observation, dict):
            return selected_action
        market = selected_action.get("market", [])
        if not isinstance(market, list):
            return selected_action
        # Truthy malformed rows are outside the reviewed donor envelope.
        if any(row and not isinstance(row, list) for row in market):
            return selected_action

        public_market = observation.get("market")
        if not isinstance(public_market, dict):
            return selected_action
        params = public_market.get("params")
        # The donor is bound to the pinned default market curves only.
        if params:
            return selected_action
        inventory = public_market.get("inventory")
        if not isinstance(inventory, Mapping):
            return selected_action
        if not isinstance(post_unit_shed, Mapping):
            return selected_action

        # Preserve raw falsey slots exactly.  Copy only the outer list so a sort
        # cannot mutate the selected action or any row object.
        raw = list(market)
        ordered = order_leading_sells(
            raw,
            inventory,
            post_unit_shed,
            price_at=price_at,
            priced_items=priced_items,
        )
    except (TypeError, ValueError, KeyError, IndexError, OverflowError):
        return selected_action

    if ordered == raw:
        return selected_action
    out = dict(selected_action)
    out["market"] = ordered
    return out
