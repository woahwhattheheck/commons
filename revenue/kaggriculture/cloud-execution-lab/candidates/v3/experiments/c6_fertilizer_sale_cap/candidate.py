# SPDX-License-Identifier: Apache-2.0
"""C6 evaluation arm: protect already-committed V219 fertilizer loading.

This experiment stays outside ``overlay/**`` and therefore changes no production
submission bytes.  It runs the exact frozen V3.1 R04 tuple, then may cancel only
FERTILIZER quantity that E184 booked on the *same callback*.  Cancellation is
allowed only to preserve fertilizer for already-confirmed V219 workers whose
route state says they still need to load it.  Native/tape sales, V233 credit
sales, unrelated E184 debt, worker commands, purchases, hires and other market
rows are never rewritten.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
MODULE_ROOT = OVERLAY if OVERLAY.is_dir() else V3_ROOT
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

import r04_full_router as base  # noqa: E402


LIVE_BASELINE = {
    "horizon": 8,
    "opening": 0,
    "row_order": True,
    "evening_flush": True,
    "sale_fertilizer": True,
    "cattle_early": True,
}
_BASE_AGENT = base.install(**LIVE_BASELINE)

REPORT = {
    "fert_advance_callbacks_seen": 0,
    "fert_advance_units_seen": 0,
    "fert_reserve_callbacks": 0,
    "fert_reserve_target_units": 0,
    "fert_advance_units_withheld": 0,
}


def _quantity(value):
    """Return a non-negative JSON integer, rejecting bool/float/string aliases."""
    return value if type(value) is int and value >= 0 else None


def snapshot_fertilizer_debts(state):
    """Strictly snapshot only E184's outstanding FERTILIZER debt by due step."""
    debts = getattr(state, "sale_window_debts", {})
    if not isinstance(debts, dict):
        return None
    result = {}
    for due_step, ledger in debts.items():
        if type(due_step) is not int or not isinstance(ledger, dict):
            return None
        quantity = _quantity(ledger.get("FERTILIZER", 0))
        if quantity is None:
            return None
        if quantity:
            result[due_step] = quantity
    return result


def new_fertilizer_bookings(before, after):
    """Positive same-callback FERTILIZER debt increments only."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return None
    booked = {}
    for due_step, quantity in after.items():
        if type(due_step) is not int or _quantity(quantity) is None:
            return None
        previous = before.get(due_step, 0)
        if _quantity(previous) is None:
            return None
        increment = quantity - previous
        if increment > 0:
            booked[due_step] = increment
    return booked


def _pre_parent_snapshot(player, step):
    """Snapshot inherited debt; a rewind is a fresh R04 DayState by contract."""
    policy = getattr(base, "_POLICY", None)
    if policy is None:
        return {}
    players = getattr(policy, "players", None)
    if not isinstance(players, dict):
        return None
    state = players.get(player)
    if state is None:
        return {}
    last_step = getattr(state, "last_step", None)
    if type(last_step) is not int:
        return None
    if step <= last_step:
        return {}
    return snapshot_fertilizer_debts(state)


def v219_fertilizer_reserve(observation):
    """Units still needed by confirmed day-24/day-27 V219 fertilizer loaders.

    V219 creates two crop workers on day 24, each with a five-unit loading target,
    and one dedicated fertilizer worker on day 27 with a ten-unit target.  We use
    the live V219 role objects rather than predicting route state from the tape.
    """
    step = observation.get("step") if isinstance(observation, dict) else None
    player = observation.get("player") if isinstance(observation, dict) else None
    if type(step) is not int or type(player) is not int:
        return None
    day = step // 24
    if day not in (24, 27):
        return 0

    states = getattr(base, "_V219_STATES", None)
    if not isinstance(states, dict):
        return None
    state = states.get(player)
    if state is None:
        return 0
    if not isinstance(state, dict):
        return None
    if state.get("committed") is not True or state.get("day") != day:
        return 0
    workers = state.get("workers")
    if not isinstance(workers, dict):
        return None

    private = observation.get("private")
    if not isinstance(private, dict) or not isinstance(private.get("inventories"), list):
        return None
    inventories = private["inventories"]
    reserve = 0
    for actor, role in workers.items():
        if type(actor) is not int or actor < 0 or actor >= len(inventories):
            return None
        if not isinstance(role, dict):
            return None
        needs = role.get("needs_fertilizer", False)
        loaded = role.get("loaded", False)
        if type(needs) is not bool or type(loaded) is not bool:
            return None
        if not needs or loaded:
            continue
        kind = role.get("kind")
        if kind not in ("crop", "fertilizer"):
            return None
        inventory = inventories[actor]
        if not isinstance(inventory, dict):
            return None
        carried = _quantity(inventory.get("FERTILIZER", 0))
        if carried is None:
            return None
        target = 10 if kind == "fertilizer" else 5
        reserve += max(0, target - carried)
    return reserve


def _fertilizer_sell_rows(action):
    market = action.get("market") if isinstance(action, dict) else None
    if not isinstance(market, list):
        return None
    rows = []
    total = 0
    for index, order in enumerate(market):
        if not isinstance(order, list) or not order:
            return None
        if len(order) >= 2 and order[:2] == ["SELL", "FERTILIZER"]:
            if len(order) < 3:
                return None
            quantity = _quantity(order[2])
            if quantity is None:
                return None
            rows.append((index, quantity))
            total += quantity
    return rows, total


def _projected_fertilizer_after_sales(observation, action):
    parsed = _fertilizer_sell_rows(action)
    if parsed is None:
        return None
    _, selling = parsed
    try:
        view = base.FarmView(observation)
        stock = base.projected_shed(action, view).get("FERTILIZER", 0)
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    stock = _quantity(stock)
    if stock is None:
        return None
    return max(0, stock - selling)


def _refunded_debts(state, bookings, amount):
    """Return a copied debt ledger with exactly ``amount`` same-call units restored."""
    debts = getattr(state, "sale_window_debts", None)
    if not isinstance(debts, dict) or _quantity(amount) is None:
        return None
    changed = copy.deepcopy(debts)
    remaining = amount
    for due_step in sorted(bookings):
        if remaining <= 0:
            break
        booked = _quantity(bookings[due_step])
        ledger = changed.get(due_step)
        if booked is None or not isinstance(ledger, dict):
            return None
        current = _quantity(ledger.get("FERTILIZER", 0))
        if current is None:
            return None
        cancel = min(booked, remaining)
        if current < cancel:
            return None
        left = current - cancel
        if left:
            ledger["FERTILIZER"] = left
        else:
            ledger.pop("FERTILIZER", None)
            if not ledger:
                changed.pop(due_step, None)
        remaining -= cancel
    return changed if remaining == 0 else None


def cap_owned_fertilizer_advance(observation, action, state, bookings, reserve):
    """Cancel only accounting-owned E184 FERTILIZER advance needed by V219."""
    if reserve is None or reserve <= 0 or not bookings:
        return action
    if any(type(step) is not int or _quantity(qty) is None for step, qty in bookings.items()):
        return action
    owned = sum(bookings.values())
    if owned <= 0:
        return action

    parsed = _fertilizer_sell_rows(action)
    if parsed is None:
        return action
    rows, selling = parsed
    # E184 blocks an item already sold by its parent. Therefore a same-callback
    # FERT booking must correspond to one newly-created FERT row and to no parent
    # FERT sale. Refuse to infer ownership if that exact invariant is not visible.
    if len(rows) != 1 or selling != owned:
        return action

    remaining_stock = _projected_fertilizer_after_sales(observation, action)
    if remaining_stock is None or remaining_stock >= reserve:
        return action
    withhold = min(owned, reserve - remaining_stock)
    if withhold <= 0:
        return action

    refunded = _refunded_debts(state, bookings, withhold)
    if refunded is None:
        return action

    result = copy.deepcopy(action)
    row_index, quantity = rows[0]
    if withhold == quantity:
        del result["market"][row_index]
    else:
        result["market"][row_index][2] = quantity - withhold
    state.sale_window_debts = refunded

    REPORT["fert_reserve_callbacks"] += 1
    REPORT["fert_reserve_target_units"] += reserve
    REPORT["fert_advance_units_withheld"] += withhold
    return result


def agent(observation, configuration=None):
    player = observation.get("player") if isinstance(observation, dict) else None
    step = observation.get("step") if isinstance(observation, dict) else None
    strict_key = type(player) is int and type(step) is int
    before = _pre_parent_snapshot(player, step) if strict_key else None

    action = _BASE_AGENT(observation, configuration)
    if before is None or not strict_key:
        return action
    policy = getattr(base, "_POLICY", None)
    players = getattr(policy, "players", None) if policy is not None else None
    if not isinstance(players, dict):
        return action
    state = players.get(player)
    if state is None:
        return action
    after = snapshot_fertilizer_debts(state)
    bookings = new_fertilizer_bookings(before, after)
    if bookings is None or not bookings:
        return action

    REPORT["fert_advance_callbacks_seen"] += 1
    REPORT["fert_advance_units_seen"] += sum(bookings.values())
    reserve = v219_fertilizer_reserve(observation)
    return cap_owned_fertilizer_advance(observation, action, state, bookings, reserve)


agent.telemetry = REPORT
