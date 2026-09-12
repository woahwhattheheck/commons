# SPDX-License-Identifier: Apache-2.0
"""Current-ABI research port of submitted V3.1 H4 strawberry top-up.

This module deliberately does not call a producer/controller.  It transforms one
already-selected action using explicit, authenticated state supplied by the caller.

Historical authority:
  commit: a90d888f03987ef0b35cfd20ec3519c6144db08a
  path: revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/r04_h4_strawberry.py
  Git blob: d6e3ffb76856ff171dab2a45b4d3c1788f2b2cb8

The theorem preserved here is narrow: an existing STRAWBERRY SELL may be enlarged
only by quantities already authored as near-future STRAWBERRY SELLs, bounded by
projected current shed stock and per-due-step sale-window debt.  No market row is
created or reordered.
"""

from __future__ import annotations

import copy

DONOR_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
DONOR_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/"
    "r04_h4_strawberry.py"
)
DONOR_BLOB = "d6e3ffb76856ff171dab2a45b4d3c1788f2b2cb8"

ITEM = "STRAWBERRY"
SELL = "SELL"
BUY_PRODUCT = "BUY_PRODUCT"
PICKUP = "PICKUP"
PLACE = "PLACE"


class BoundaryError(ValueError):
    """Raised only for a malformed explicit current-ABI boundary."""


def _plain_int(value, name):
    if type(value) is not int:
        raise BoundaryError(f"{name} must be a plain int")
    return value


def _list(value, name):
    if not isinstance(value, list):
        raise BoundaryError(f"{name} must be a list")
    return value


def _command(raw):
    return raw if isinstance(raw, (list, tuple)) else None


def _order_quantity(raw):
    if not isinstance(raw, (list, tuple)) or len(raw) < 3:
        return None
    try:
        return max(0, int(raw[2]))
    except (TypeError, ValueError, OverflowError):
        return None


def _is(raw, op, item=None):
    row = _command(raw)
    if row is None or not row:
        return False
    if row[0] != op:
        return False
    return item is None or (len(row) > 1 and row[1] == item)


def _unit_commands(action):
    farmer = action.get("farmer", ["PASS"])
    hands = action.get("hands", [])
    if not isinstance(hands, list):
        raise BoundaryError("action.hands must be a list")
    commands = [farmer, *hands]
    if any(_command(c) is None for c in commands):
        raise BoundaryError("unit commands must be list/tuple rows")
    return commands


def _normalize_debts(debts):
    if not isinstance(debts, dict):
        raise BoundaryError("sale_window_debts must be a dict")
    normalized = {}
    for raw_step, raw_items in debts.items():
        due = _plain_int(raw_step, "debt due step")
        if not isinstance(raw_items, dict):
            raise BoundaryError("debt item map must be a dict")
        items = {}
        for item, raw_amount in raw_items.items():
            if not isinstance(item, str):
                raise BoundaryError("debt item key must be a string")
            try:
                amount = int(raw_amount)
            except (TypeError, ValueError, OverflowError) as exc:
                raise BoundaryError("debt amount must be int-coercible") from exc
            if amount < 0:
                raise BoundaryError("debt amount must be nonnegative")
            items[item] = amount
        normalized[due] = items
    return normalized


def _identity(action, debts, reason, **extra):
    receipt = {
        "applied": False,
        "reason": reason,
        "donor_commit": DONOR_COMMIT,
        "donor_blob": DONOR_BLOB,
    }
    receipt.update(extra)
    return action, debts, receipt


def reconcile_strawberry_current(
    action,
    *,
    enabled,
    step,
    advance_start,
    last_step,
    sale_horizon,
    projected_shed,
    strawberry_price,
    future_actions,
    sale_window_debts,
    queued_commands,
    actor_inventories,
    animal_items,
):
    """Top up one existing STRAWBERRY SELL at the current selected-action boundary.

    ``future_actions`` must be a mapping from every due step in the authenticated
    bounded future window to an already-authored selected action.  The function
    never calls a producer and never creates a market row.

    Returns ``(action, debts, receipt)``.  On any semantic ineligibility the exact
    input ``action`` and ``sale_window_debts`` objects are returned.  Malformed
    boundary containers fail closed with ``BoundaryError`` instead of guessing.
    """

    if type(enabled) is not bool:
        raise TypeError("enabled must be a literal bool")
    if not enabled:
        return _identity(action, sale_window_debts, "disabled")

    step = _plain_int(step, "step")
    advance_start = _plain_int(advance_start, "advance_start")
    last_step = _plain_int(last_step, "last_step")
    sale_horizon = _plain_int(sale_horizon, "sale_horizon")
    if sale_horizon < 1 or last_step <= 0 or advance_start < 0:
        raise BoundaryError("invalid horizon/step bounds")
    if step < advance_start or step >= last_step:
        return _identity(action, sale_window_debts, "outside-window")

    if not isinstance(action, dict):
        raise BoundaryError("action must be a dict")
    market = _list(action.get("market", []), "action.market")
    commands = _unit_commands(action)

    sell_rows = []
    for index, order in enumerate(market):
        if _is(order, SELL, ITEM):
            quantity = _order_quantity(order)
            if quantity is None:
                return _identity(action, sale_window_debts, "malformed-current-sell")
            sell_rows.append((index, quantity))
    if len(sell_rows) != 1:
        return _identity(action, sale_window_debts, "requires-one-current-sell")

    for order in market:
        if _is(order, BUY_PRODUCT, ITEM):
            return _identity(action, sale_window_debts, "current-buy-product")

    try:
        price = int(strawberry_price)
    except (TypeError, ValueError, OverflowError) as exc:
        raise BoundaryError("strawberry_price must be int-coercible") from exc
    if price < 2:
        return _identity(action, sale_window_debts, "price-floor")

    if not isinstance(queued_commands, (list, tuple)):
        raise BoundaryError("queued_commands must be a list/tuple")
    if any(_command(c) is None for c in queued_commands):
        raise BoundaryError("queued commands must be list/tuple rows")
    if any(_is(command, PICKUP, ITEM) for command in queued_commands):
        return _identity(action, sale_window_debts, "queued-pickup")
    if any(_is(command, PICKUP, ITEM) for command in commands):
        return _identity(action, sale_window_debts, "current-pickup")

    if not isinstance(actor_inventories, list) or len(actor_inventories) != len(commands):
        raise BoundaryError("actor_inventories must match farmer+hands cardinality")
    if any(not isinstance(inventory, dict) for inventory in actor_inventories):
        raise BoundaryError("actor inventory must be a dict")
    if not isinstance(animal_items, (set, frozenset, list, tuple)):
        raise BoundaryError("animal_items must be a collection")
    animals = set(animal_items)
    for actor, command in enumerate(commands):
        if _is(command, PLACE) and len(command) > 1 and command[1] in animals:
            try:
                owned = int(actor_inventories[actor].get(command[1], 0))
            except (TypeError, ValueError, OverflowError) as exc:
                raise BoundaryError("animal inventory must be int-coercible") from exc
            if owned > 0:
                return _identity(action, sale_window_debts, "animal-place-fallback")

    if not isinstance(projected_shed, dict):
        raise BoundaryError("projected_shed must be a dict")
    row_index, current_quantity = sell_rows[0]
    try:
        projected = int(projected_shed.get(ITEM, 0))
    except (TypeError, ValueError, OverflowError) as exc:
        raise BoundaryError("projected shed quantity must be int-coercible") from exc
    available = max(0, projected - current_quantity)
    if not available:
        return _identity(action, sale_window_debts, "no-projected-surplus")

    if not isinstance(future_actions, dict):
        raise BoundaryError("future_actions must be a dict keyed by plain-int step")
    if any(type(k) is not int for k in future_actions):
        raise BoundaryError("future action keys must be plain ints")

    # Preserve the V3.1 H4/E184 horizon: before step 144 only one step may advance,
    # and no advance may cross the 72-step day boundary or the terminal step.
    horizon = sale_horizon if step >= 144 else 1
    end = min(last_step, step + horizon, (step // 72 + 1) * 72 - 1)
    if end <= step:
        return _identity(action, sale_window_debts, "empty-future-window")

    for due in range(step + 1, end + 1):
        if due not in future_actions:
            return _identity(
                action,
                sale_window_debts,
                "incomplete-future-window",
                missing_due_step=due,
            )

    original_debts = _normalize_debts(sale_window_debts)
    reservations = []
    remaining_stock = available

    for due_step in range(step + 1, end + 1):
        future = future_actions[due_step]
        if not isinstance(future, dict):
            return _identity(
                action,
                sale_window_debts,
                "malformed-future-action",
                due_step=due_step,
            )
        try:
            future_commands = _unit_commands(future)
            future_market = _list(future.get("market", []), "future.market")
        except BoundaryError:
            return _identity(
                action,
                sale_window_debts,
                "malformed-future-action",
                due_step=due_step,
            )

        if any(_is(command, PICKUP, ITEM) for command in future_commands):
            break
        if any(_is(order, BUY_PRODUCT, ITEM) for order in future_market):
            break

        planned = 0
        for order in future_market:
            if _is(order, SELL, ITEM):
                quantity = _order_quantity(order)
                if quantity is None:
                    return _identity(
                        action,
                        sale_window_debts,
                        "malformed-future-sell",
                        due_step=due_step,
                    )
                planned += quantity

        already_advanced = original_debts.get(due_step, {}).get(ITEM, 0)
        amount = min(remaining_stock, max(0, planned - already_advanced))
        if amount:
            reservations.append((due_step, amount))
            remaining_stock -= amount
        if not remaining_stock:
            break

    added = sum(amount for _, amount in reservations)
    if not added:
        return _identity(action, sale_window_debts, "no-backed-future-sale")

    result = copy.deepcopy(action)
    result["market"][row_index][2] = current_quantity + added

    debts = {due: dict(items) for due, items in original_debts.items()}
    for due_step, amount in reservations:
        due = debts.setdefault(due_step, {})
        due[ITEM] = due.get(ITEM, 0) + amount

    receipt = {
        "applied": True,
        "reason": "strawberry-topup",
        "item": ITEM,
        "row_index": row_index,
        "original_quantity": current_quantity,
        "added_quantity": added,
        "final_quantity": current_quantity + added,
        "reservations": tuple(reservations),
        "window_end": end,
        "donor_commit": DONOR_COMMIT,
        "donor_blob": DONOR_BLOB,
    }
    return result, debts, receipt
