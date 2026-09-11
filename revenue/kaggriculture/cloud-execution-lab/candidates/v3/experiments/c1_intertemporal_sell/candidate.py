# SPDX-License-Identifier: Apache-2.0
"""C1 default-off experiment: defer selected native hour-20 SELLs past town demand.

The official engine processes player market rows before deterministic town demand and
refreshes prices afterward. Live V3.1 already runs EVENING_FLUSH at hours 21-23. This
experiment therefore blanks only *native-tape-owned* hour-20 SELL rows for flush items
that an already-unlocked shop consumes at that same step, leaving their stock for the
incumbent hour-21 flush.

This carrier is deliberately stricter than the original development probe. It preserves
raw market indices with [] placeholders; rejects mixed/non-native market rows; rejects
E184/native-advance debt ownership; and rejects current HARVEST/COLLECT_FERTILIZER or
capacity ambiguity that could make holding shed stock for one callback destroy cargo.
No new market order, worker action, quantity, movement, hidden-rival inference, or package
input is introduced.
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
TARGET_HOUR = 20
FLUSH_ITEMS = frozenset(("WOOL", "MILK", "STRAWBERRY", "MELON"))
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
    "by_item": {item: 0 for item in sorted(FLUSH_ITEMS)},
}

_MISSING = object()


def _cfg_value(configuration, key, default):
    if configuration is None:
        return default
    if isinstance(configuration, dict):
        return configuration.get(key, default)
    getter = getattr(configuration, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except Exception:
            return _MISSING
    return getattr(configuration, key, default)


def _standard_config(configuration) -> bool:
    for key, expected in (
        ("turnsPerDay", TURN_PER_DAY),
        ("townShopSellInterval", SHOP_INTERVAL),
        ("shedCapacity", SHED_CAPACITY),
        ("episodeSteps", EPISODE_STEPS),
    ):
        value = _cfg_value(configuration, key, expected)
        if type(value) is not int or value != expected:
            return False
    market_params = _cfg_value(configuration, "marketParams", None)
    if market_params is not None:
        if not isinstance(market_params, dict) or market_params:
            return False
    return True


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
    if not isinstance(action, dict):
        return None
    if "farmer" not in action or "hands" not in action:
        return None
    farmer = action["farmer"]
    hands = action["hands"]
    if not isinstance(farmer, list) or not isinstance(hands, list):
        return None
    commands = [farmer, *hands]
    if any(not isinstance(command, list) for command in commands):
        return None
    return commands


def _debt_owned_items(sale_state, step: int) -> set[str] | None:
    """Items whose current SELL may be coupled to parent sale accounting."""
    if sale_state is None:
        return set()
    owned = set()
    advanced = getattr(sale_state, "advanced_sales", {})
    if advanced is None:
        advanced = {}
    if not isinstance(advanced, dict):
        return None
    for item, quantity in advanced.items():
        if not isinstance(item, str) or type(quantity) is not int or quantity < 0:
            return None
        if quantity > 0:
            owned.add(item)

    debts = getattr(sale_state, "sale_window_debts", {})
    if debts is None:
        debts = {}
    if not isinstance(debts, dict):
        return None
    for due_step, by_item in debts.items():
        if type(due_step) is not int or due_step < 0 or not isinstance(by_item, dict):
            return None
        if due_step <= step:
            continue
        for item, quantity in by_item.items():
            if not isinstance(item, str) or type(quantity) is not int or quantity < 0:
                return None
            if quantity > 0:
                owned.add(item)
    return owned


def _demanded_flush_items(town) -> set[str] | None:
    if not isinstance(town, dict):
        return None
    shops = town.get("unlocked_shops")
    if not isinstance(shops, list):
        return None
    demanded = set()
    for shop in shops:
        if not isinstance(shop, str) or shop not in SHOP_PRODUCTS:
            return None
        demanded.update(SHOP_PRODUCTS[shop])
    return demanded & FLUSH_ITEMS


def apply_intertemporal_deferral(
    observation,
    action,
    *,
    native_market,
    sale_state=None,
    configuration=None,
):
    """Return action with proven native hour-20 demand-exposed SELL rows blanked.

    Every reject returns the exact parent object. Successful transforms copy once and keep
    market list length/indexes unchanged; each deferred row becomes an empty placeholder.
    """
    if not isinstance(observation, dict) or not isinstance(action, dict):
        return action
    if not _standard_config(configuration):
        return action

    step = observation.get("step")
    player = observation.get("player")
    if type(step) is not int or step < TURN_PER_DAY or step >= EPISODE_STEPS - 2:
        return action
    if step % TURN_PER_DAY != TARGET_HOUR:
        return action
    if type(player) is not int or player not in (0, 1):
        return action

    demanded = _demanded_flush_items(observation.get("town"))
    if not demanded:
        return action

    farms = observation.get("farms")
    private = observation.get("private")
    if not isinstance(farms, list) or len(farms) != 2 or not isinstance(private, dict):
        return action

    shed_total = _strict_nonnegative_mapping(private.get("shed"))
    inventories = private.get("inventories")
    if shed_total is None or not isinstance(inventories, list) or not inventories:
        return action
    cargo_total = 0
    for inventory in inventories:
        subtotal = _strict_nonnegative_mapping(inventory)
        if subtotal is None:
            return action
        cargo_total += subtotal
    if shed_total + cargo_total > SHED_CAPACITY:
        return action

    commands = _current_commands(action)
    if commands is None:
        return action
    for command in commands:
        if command and command[0] in INVENTORY_PRODUCERS:
            return action

    market = action.get("market")
    current_counter = _sell_counter(market)
    native_counter = _sell_counter(native_market)
    # Ownership theorem: the parent output must contain exactly the selected tape's SELL-only
    # multiset. Any E184/V233/V219/other synthesized row or quantity mutation fails closed.
    if current_counter is None or native_counter is None or current_counter != native_counter:
        return action
    if not current_counter:
        return action

    debt_owned = _debt_owned_items(sale_state, step)
    if debt_owned is None:
        return action

    replacements = []
    for index, row in enumerate(market):
        if row == []:
            continue
        parsed = _strict_market_row(row)
        if parsed is None:
            return action
        _, item, quantity = parsed
        if item in demanded and item not in debt_owned:
            replacements.append((index, item, quantity))

    if not replacements:
        return action

    result = copy.deepcopy(action)
    for index, _, _ in replacements:
        result["market"][index] = []

    REPORT["callbacks"] += 1
    REPORT["deferrals"] += 1
    REPORT["deferred_rows"] += len(replacements)
    REPORT["deferred_requested_qty"] += sum(quantity for _, _, quantity in replacements)
    for _, item, _ in replacements:
        REPORT["by_item"][item] += 1
    return result


def _parent_state_and_native(player: int, step: int):
    policy = getattr(base, "_POLICY", None)
    players = getattr(policy, "players", None)
    tapes = getattr(policy, "tapes", None)
    if not isinstance(players, dict) or not isinstance(tapes, list):
        return None, None
    state = players.get(player)
    if state is None:
        return None, None
    plan = getattr(state, "plan", None)
    if type(plan) is not int or plan < 0 or plan >= len(tapes):
        return None, None
    tape = tapes[plan]
    if not isinstance(tape, list) or step < 0 or step >= len(tape):
        return None, None
    native = tape[step]
    if not isinstance(native, dict):
        return None, None
    return state, native.get("market")


def agent(observation, configuration=None):
    parent = _BASE_AGENT(observation, configuration)
    if not isinstance(observation, dict):
        return parent
    step = observation.get("step")
    player = observation.get("player")
    if type(step) is not int or type(player) is not int:
        return parent
    state, native_market = _parent_state_and_native(player, step)
    if native_market is None:
        return parent
    return apply_intertemporal_deferral(
        observation,
        parent,
        native_market=native_market,
        sale_state=state,
        configuration=configuration,
    )


agent.telemetry = REPORT
