# SPDX-License-Identifier: Apache-2.0
"""C1 default-off experiment: defer proven-native hour-20 STRAWBERRY sales.

The official engine processes unit actions, then player market rows, then deterministic
town-shop consumption and price refresh. Live frozen V3.1 already flushes residual
STRAWBERRY at hours 21-23. C1 therefore tests one narrow timing factor: retain a proven
native hour-20 STRAWBERRY sale for one callback when a currently unlocked shop consumes
STRAWBERRY at that same town tick.

This repaired carrier deliberately narrows the original WOOL/MILK/STRAWBERRY hypothesis.
Frozen V231 can synthesize/touch MILK sale quantity and V233 can synthesize WOOL sales;
a final market multiset can therefore look native after one incumbent layer cancels a
native row and another replaces it. Neither layer synthesizes STRAWBERRY. For the sole
remaining target, C1 snapshots E184/native sale-accounting state *before* the parent call
and requires no current STRAWBERRY ownership plus no new future STRAWBERRY reservation
across the callback. Only then can current-vs-native SELL equality establish provenance.

Every rejection returns the exact parent action. A successful transform preserves raw
market indices with ``[]`` and changes no worker command, quantity, row ordering, package
input, default, or hidden-rival state.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import copy
import sys

V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

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

TURN_PER_DAY = 24
SHOP_INTERVAL = 4
SHED_CAPACITY = 100
EPISODE_STEPS = 720
MAX_MARKET_ORDERS = 10
TARGET_HOUR = 20
TARGET_ITEM = "STRAWBERRY"
INVENTORY_PRODUCERS = frozenset(("HARVEST", "COLLECT_FERTILIZER"))
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

REPORT = {
    "callbacks": 0,
    "deferrals": 0,
    "deferred_rows": 0,
    "deferred_requested_qty": 0,
    "by_item": {TARGET_ITEM: 0},
}

_MISSING = object()


def _cfg_value(configuration, key):
    """Read an explicitly present config field; absence never inherits a default."""
    if configuration is None:
        return _MISSING
    if isinstance(configuration, dict):
        return configuration[key] if key in configuration else _MISSING
    getter = getattr(configuration, "get", None)
    if callable(getter):
        try:
            return getter(key, _MISSING)
        except Exception:
            return _MISSING
    return getattr(configuration, key, _MISSING)


def _standard_config(configuration) -> bool:
    for key, expected in (
        ("turnsPerDay", TURN_PER_DAY),
        ("townShopSellInterval", SHOP_INTERVAL),
        ("shedCapacity", SHED_CAPACITY),
        ("episodeSteps", EPISODE_STEPS),
        ("maxMarketOrdersPerTurn", MAX_MARKET_ORDERS),
    ):
        value = _cfg_value(configuration, key)
        if type(value) is not int or value != expected:
            return False
    market_params = _cfg_value(configuration, "marketParams")
    return isinstance(market_params, dict) and not market_params


def _strict_nonnegative_mapping(mapping) -> int | None:
    if not isinstance(mapping, dict):
        return None
    total = 0
    for key, value in mapping.items():
        if not isinstance(key, str) or type(value) is not int or value < 0:
            return None
        total += value
    return total


def _strict_market_row(row):
    if not isinstance(row, list) or len(row) != 3:
        return None
    op, item, quantity = row
    if op != "SELL" or not isinstance(item, str) or type(quantity) is not int or quantity <= 0:
        return None
    return op, item, quantity


def _sell_counter(rows):
    if not isinstance(rows, list):
        return None
    normalized = []
    for row in rows:
        if row == []:
            continue
        parsed = _strict_market_row(row)
        if parsed is None:
            return None
        normalized.append(parsed)
    return Counter(normalized)


def _current_commands(action):
    if not isinstance(action, dict) or "farmer" not in action or "hands" not in action:
        return None
    farmer = action["farmer"]
    hands = action["hands"]
    if not isinstance(farmer, list) or not isinstance(hands, list):
        return None
    commands = [farmer, *hands]
    if any(not isinstance(command, list) for command in commands):
        return None
    return commands


def snapshot_sale_provenance(sale_state, step: int):
    """Strict immutable E184/native-sale snapshot for STRAWBERRY provenance.

    Full accounting containers are validated so poison in an unrelated cell cannot be
    hidden by the parent popping/pruning it. The returned fields contain only the target
    facts needed by C1's ownership theorem.
    """
    if sale_state is None or type(step) is not int:
        return None

    advanced = getattr(sale_state, "advanced_sales", _MISSING)
    if not isinstance(advanced, dict):
        return None
    for item, quantity in advanced.items():
        if item not in base.PRODUCTS or type(quantity) is not int or quantity < 0:
            return None

    sale_due_step = getattr(sale_state, "sale_due_step", _MISSING)
    if type(sale_due_step) is not int or sale_due_step < -1 or sale_due_step > base.LAST_STEP:
        return None

    debts = getattr(sale_state, "sale_window_debts", _MISSING)
    if not isinstance(debts, dict):
        return None
    future_target = []
    current_target = 0
    for due_step, by_item in debts.items():
        if type(due_step) is not int or due_step < 0 or due_step > base.LAST_STEP:
            return None
        if not isinstance(by_item, dict):
            return None
        for item, quantity in by_item.items():
            if item not in base.PRODUCTS or type(quantity) is not int or quantity < 0:
                return None
        quantity = by_item.get(TARGET_ITEM, 0)
        if due_step == step:
            current_target = quantity
        elif due_step > step and quantity:
            future_target.append((due_step, quantity))

    return {
        "advanced_target": advanced.get(TARGET_ITEM, 0),
        "sale_due_step": sale_due_step,
        "current_target_debt": current_target,
        "future_target_debts": tuple(sorted(future_target)),
    }


def _proven_target_sale_ownership(pre_snapshot, post_snapshot) -> bool:
    """Require no incumbent STRAWBERRY cancellation or synthesis this callback."""
    if not isinstance(pre_snapshot, dict) or not isinstance(post_snapshot, dict):
        return False
    required = {
        "advanced_target", "sale_due_step", "current_target_debt", "future_target_debts"
    }
    if set(pre_snapshot) != required or set(post_snapshot) != required:
        return False
    for snap in (pre_snapshot, post_snapshot):
        if type(snap["advanced_target"]) is not int or snap["advanced_target"] < 0:
            return False
        if type(snap["sale_due_step"]) is not int:
            return False
        if type(snap["current_target_debt"]) is not int or snap["current_target_debt"] < 0:
            return False
        if not isinstance(snap["future_target_debts"], tuple):
            return False

    # No legacy/native one-turn STRAWBERRY advance may own the current row, and no E184
    # debt due now may subtract it before C1 sees the parent output.
    if pre_snapshot["advanced_target"] or pre_snapshot["current_target_debt"]:
        return False

    # Post-288 E184 resets legacy advanced_sales. Any target value here is anomalous.
    if post_snapshot["advanced_target"] or post_snapshot["current_target_debt"]:
        return False

    # reserve_sales only adds future debt. Exact equality proves this callback did not
    # synthesize a future-tape STRAWBERRY SELL into the current parent market.
    return pre_snapshot["future_target_debts"] == post_snapshot["future_target_debts"]


def _demanded_target(town) -> bool:
    if not isinstance(town, dict):
        return False
    shops = town.get("unlocked_shops")
    if not isinstance(shops, list):
        return False
    demanded = set()
    for shop in shops:
        if not isinstance(shop, str) or shop not in SHOP_PRODUCTS:
            return False
        demanded.update(SHOP_PRODUCTS[shop])
    return TARGET_ITEM in demanded


def apply_intertemporal_deferral(
    observation,
    action,
    *,
    native_market,
    pre_sale_snapshot=None,
    post_sale_snapshot=None,
    configuration=None,
):
    """Blank proven-native hour-20 STRAWBERRY SELL rows at their exact raw indices."""
    if not isinstance(observation, dict) or not isinstance(action, dict):
        return action
    if not _standard_config(configuration):
        return action

    step = observation.get("step")
    player = observation.get("player")
    if type(step) is not int or step < base.ADVANCE_START or step >= EPISODE_STEPS - 2:
        return action
    if step % TURN_PER_DAY != TARGET_HOUR:
        return action
    if type(player) is not int or player not in (0, 1):
        return action
    if not _demanded_target(observation.get("town")):
        return action
    if not _proven_target_sale_ownership(pre_sale_snapshot, post_sale_snapshot):
        return action

    farms = observation.get("farms")
    private = observation.get("private")
    if not isinstance(farms, list) or len(farms) != 2 or not isinstance(private, dict):
        return action

    commands = _current_commands(action)
    if commands is None:
        return action
    inventories = private.get("inventories")
    if not isinstance(inventories, list) or len(inventories) != len(commands):
        return action

    shed_total = _strict_nonnegative_mapping(private.get("shed"))
    if shed_total is None:
        return action
    cargo_total = 0
    for inventory in inventories:
        subtotal = _strict_nonnegative_mapping(inventory)
        if subtotal is None:
            return action
        cargo_total += subtotal
    if shed_total + cargo_total > SHED_CAPACITY:
        return action

    for command in commands:
        if command and command[0] in INVENTORY_PRODUCERS:
            return action

    market = action.get("market")
    current_counter = _sell_counter(market)
    native_counter = _sell_counter(native_market)
    if current_counter is None or native_counter is None or current_counter != native_counter:
        return action
    if not current_counter:
        return action

    replacements = []
    for index, row in enumerate(market):
        if row == []:
            continue
        parsed = _strict_market_row(row)
        if parsed is None:
            return action
        _, item, quantity = parsed
        if item == TARGET_ITEM:
            replacements.append((index, quantity))

    if not replacements:
        return action

    result = copy.deepcopy(action)
    for index, _ in replacements:
        result["market"][index] = []

    REPORT["callbacks"] += 1
    REPORT["deferrals"] += 1
    REPORT["deferred_rows"] += len(replacements)
    REPORT["deferred_requested_qty"] += sum(quantity for _, quantity in replacements)
    REPORT["by_item"][TARGET_ITEM] += len(replacements)
    return result


def _pre_parent_context(observation):
    if not isinstance(observation, dict):
        return None
    step = observation.get("step")
    player = observation.get("player")
    if type(step) is not int or type(player) is not int or player not in (0, 1):
        return None
    policy = getattr(base, "_POLICY", None)
    players = getattr(policy, "players", None)
    tapes = getattr(policy, "tapes", None)
    if not isinstance(players, dict) or not isinstance(tapes, list):
        return None
    state = players.get(player)
    if state is None:
        return None
    plan = getattr(state, "plan", None)
    if type(plan) is not int or plan < 0 or plan >= len(tapes):
        return None
    tape = tapes[plan]
    if not isinstance(tape, list) or step < 0 or step >= len(tape):
        return None
    native = tape[step]
    if not isinstance(native, dict) or not isinstance(native.get("market"), list):
        return None
    snapshot = snapshot_sale_provenance(state, step)
    if snapshot is None:
        return None
    return state, copy.deepcopy(native["market"]), snapshot


def agent(observation, configuration=None):
    context = _pre_parent_context(observation)
    parent = _BASE_AGENT(observation, configuration)
    if context is None or not isinstance(observation, dict):
        return parent

    pre_state, native_market, pre_snapshot = context
    step = observation.get("step")
    player = observation.get("player")
    policy = getattr(base, "_POLICY", None)
    players = getattr(policy, "players", None)
    if not isinstance(players, dict):
        return parent
    post_state = players.get(player)
    # Rewind/reset/replacement means our pre-parent ownership proof no longer applies.
    if post_state is not pre_state:
        return parent
    post_snapshot = snapshot_sale_provenance(post_state, step)
    if post_snapshot is None:
        return parent

    return apply_intertemporal_deferral(
        observation,
        parent,
        native_market=native_market,
        pre_sale_snapshot=pre_snapshot,
        post_sale_snapshot=post_snapshot,
        configuration=configuration,
    )


agent.telemetry = REPORT
