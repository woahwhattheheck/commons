#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""C4 practice arm: keep E184 sale reservations from crossing a known town-demand tick.

The official engine commits both players' market rows before ``_town_consume``. A bot cannot
observe the rival's same-turn action, so C4 does *not* try to predict a quiet rival turn. It
uses only deterministic public demand: unlocked shops consume every four steps and town center
consumes every 24 steps. If E184 newly pulls an authored future SELL backward across one of
those known demand ticks, C4 rolls back only that newly-created reservation and leaves the
future authored sale in place.

C4 snapshots E184 debt before the parent call, executes the *full unmodified V3.1 parent*, then
applies its rollback to the final action. This ordering is deliberate: a zeroed E184 row remains
an explicit raw ``[]`` market slot, so C4 cannot make incumbent ROW_ORDER compact a placeholder
and shift unrelated parent rows against different rival lockstep indices.

This module lives outside ``overlay/**`` and is default-off. It changes timing only; source
custody is not an economics claim because lower pre-tick supply may also improve the rival's
quotes. Paired Delta-margin is required before promotion.
"""
from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as base  # noqa: E402

SHOP_PRODUCTS = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}
TOWN_CENTER_PRODUCTS = tuple(item for item in base.PRODUCTS if item != "FERTILIZER")
SHOP_INTERVAL = 4
CENTER_INTERVAL = 24
C4_ENABLED = False

telemetry = Counter()


def _cfg(configuration, name, default):
    if configuration is None:
        return default
    if isinstance(configuration, dict):
        return configuration.get(name, default)
    return getattr(configuration, name, default)


def _standard_demand_clock(configuration):
    shop = _cfg(configuration, "townShopSellInterval", SHOP_INTERVAL)
    center = _cfg(configuration, "townCenterSellInterval", CENTER_INTERVAL)
    return (
        type(shop) is int and shop == SHOP_INTERVAL
        and type(center) is int and center == CENTER_INTERVAL
    )


def _demand_items(observation, step, configuration=None):
    """Return products deterministically consumed after market on ``step``; None = unknown."""
    if type(step) is not int or step < 0 or not _standard_demand_clock(configuration):
        return None
    try:
        town = observation["town"]
        shops = town["unlocked_shops"]
    except (KeyError, TypeError):
        return None
    if not isinstance(town, dict) or not isinstance(shops, list):
        return None
    if any(not isinstance(shop, str) or shop not in SHOP_PRODUCTS for shop in shops):
        return None

    demand = set()
    if step % SHOP_INTERVAL == 0:
        for shop in shops:
            demand.update(SHOP_PRODUCTS[shop])
    if step % CENTER_INTERVAL == 0:
        demand.update(TOWN_CENTER_PRODUCTS)
    return demand


def _crosses_public_demand(observation, item, start_step, due_step, configuration=None):
    """True iff a known town-consumption tick for item occurs before the authored due step."""
    if type(start_step) is not int or type(due_step) is not int or due_step <= start_step:
        return False
    for step in range(start_step, due_step):
        demand = _demand_items(observation, step, configuration)
        if demand is None:
            return None
        if item in demand:
            return True
    return False


def _strict_nonnegative_int(value):
    return type(value) is int and value >= 0


def _debt_snapshot(state):
    debts = getattr(state, "sale_window_debts", {})
    if not isinstance(debts, dict):
        return None
    try:
        return copy.deepcopy(debts)
    except Exception:
        return None


def rollback_cross_tick_advances(action, observation, state, before_debts, configuration=None,
                                 enabled=False):
    """Undo only *new* E184 reservations that jumped over deterministic public demand.

    The function is called after the full V3.1 parent action has been composed. E184 itself
    blocks advancing an item already present in the pre-reservation market. Later parent layers
    may create a second same-item row; in that case the final action is ambiguous and C4 fails
    closed. All action/debt edits are proven first, then one copied action and one copied debt
    map replace the parent result atomically.
    """
    telemetry["calls"] += 1
    if not enabled:
        telemetry["disabled"] += 1
        return action
    if not isinstance(action, dict) or not isinstance(before_debts, dict):
        telemetry["malformed"] += 1
        return action
    try:
        step = observation["step"]
    except (KeyError, TypeError):
        telemetry["malformed"] += 1
        return action
    if type(step) is not int or step < base.ADVANCE_START or step >= base.LAST_STEP:
        return action
    if not _standard_demand_clock(configuration):
        telemetry["nonstandard_clock"] += 1
        return action

    after = getattr(state, "sale_window_debts", None)
    if not isinstance(after, dict):
        telemetry["malformed"] += 1
        return action

    per_due = {}
    per_item = {}
    for due_step, due_items in after.items():
        if type(due_step) is not int or due_step <= step or not isinstance(due_items, dict):
            telemetry["malformed"] += 1
            return action
        old_items = before_debts.get(due_step, {})
        if not isinstance(old_items, dict):
            telemetry["malformed"] += 1
            return action
        for item, amount in due_items.items():
            if item not in base.PRODUCTS or not _strict_nonnegative_int(amount):
                telemetry["malformed"] += 1
                return action
            old = old_items.get(item, 0)
            if not _strict_nonnegative_int(old) or old > amount:
                telemetry["malformed"] += 1
                return action
            delta = amount - old
            if not delta:
                continue
            crossed = _crosses_public_demand(observation, item, step, due_step, configuration)
            if crossed is None:
                telemetry["malformed"] += 1
                return action
            if crossed:
                per_due[(due_step, item)] = delta
                per_item[item] = per_item.get(item, 0) + delta

    if not per_item:
        return action

    market = action.get("market")
    if not isinstance(market, list):
        telemetry["malformed"] += 1
        return action

    edits = {}
    for item, rollback in per_item.items():
        rows = []
        for index, order in enumerate(market):
            if (isinstance(order, list) and len(order) >= 3
                    and order[0] == "SELL" and order[1] == item):
                rows.append((index, order))
        if len(rows) != 1:
            telemetry["ambiguous_sell_row"] += 1
            return action
        index, order = rows[0]
        quantity = order[2]
        if not _strict_nonnegative_int(quantity) or quantity < rollback:
            telemetry["malformed"] += 1
            return action
        edits[index] = quantity - rollback

    # All invariants proven. This is the final post-parent action, so an explicit [] remains at
    # this exact raw index and cannot be compacted by an incumbent wrapper after C4.
    out = copy.deepcopy(action)
    for index, quantity in edits.items():
        if quantity:
            out["market"][index][2] = quantity
        else:
            out["market"][index] = []

    new_debts = copy.deepcopy(after)
    for (due_step, item), rollback in per_due.items():
        remaining = new_debts[due_step][item] - rollback
        if remaining:
            new_debts[due_step][item] = remaining
        else:
            del new_debts[due_step][item]
        if not new_debts[due_step]:
            del new_debts[due_step]
    state.sale_window_debts = new_debts

    units = sum(per_item.values())
    telemetry["activations"] += 1
    telemetry["rows_rolled_back"] += len(per_item)
    telemetry["units_rolled_back"] += units
    telemetry["due_cells_rolled_back"] += len(per_due)
    return out


def c4_agent(observation, configuration=None):
    """Snapshot E184 debt, execute exact shipped parent, then apply bounded C4 rollback."""
    player = observation.get("player") if isinstance(observation, dict) else None
    before = {}
    snapshot_ok = True
    if C4_ENABLED and type(player) is int and base._POLICY is not None:
        state = base._POLICY.players.get(player)
        if state is not None:
            snapshot = _debt_snapshot(state)
            if snapshot is None:
                snapshot_ok = False
            else:
                before = snapshot

    # Use the full incumbent V3.1 composition; do not duplicate ROW_ORDER/FLUSH logic here.
    action = base.v3_agent(observation, configuration)

    if C4_ENABLED and snapshot_ok and type(player) is int and base._POLICY is not None:
        state = base._POLICY.players.get(player)
        if state is not None:
            action = rollback_cross_tick_advances(
                action, observation, state, before, configuration, enabled=True
            )
    return action


def install(host=None, horizon=None, opening=None, row_order=None, evening_flush=None,
            sale_fertilizer=None, cattle_early=None, c4_enabled=None):
    global C4_ENABLED
    base.install(host, horizon, opening, row_order, evening_flush, sale_fertilizer, cattle_early)
    if c4_enabled is not None:
        C4_ENABLED = bool(c4_enabled)
    return c4_agent


agent = install(
    None,
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
    c4_enabled=True,
)

C4_EVALUATOR_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "townShopSellInterval": 4,
    "townCenterSellInterval": 24,
    "c4_town_demand_boundary": True,
    "official_interpreter_commit": "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
}

agent.telemetry = telemetry
