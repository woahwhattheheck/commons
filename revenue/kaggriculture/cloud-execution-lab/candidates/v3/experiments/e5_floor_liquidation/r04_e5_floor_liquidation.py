# SPDX-License-Identifier: Apache-2.0
"""E5: pre-terminal floor-price liquidation experiment for live V3.1 R04.

At the penultimate action (step 717 under the standard 720-step game), the
default town schedules have already performed their last consumption tick.
For products players cannot BUY_PRODUCT and that have no farm-service use,
a SELL quoted at the hard $1 floor cannot change market inventory and cannot
recover to a better price before R04's existing step-718 liquidation.

The only intended edge is capacity release: selling otherwise-terminal shed
stock at $1 one turn early may create room for the existing final-turn DROP
to move carried inventory into the shed before terminal liquidation.
"""

from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as r04  # noqa: E402

ENABLED = False
E5_STEP = r04.LAST_STEP - 1
SAFE_ITEMS = (
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
)
_STANDARD_CONFIG = {
    "episodeSteps": 720,
    "turnsPerDay": 24,
    "maxMarketOrdersPerTurn": 10,
    "shedCapacity": 100,
    "townShopSellInterval": 4,
    "townCenterSellInterval": 24,
}

REPORT = {
    "calls": 0,
    "activations": 0,
    "rows_added": 0,
    "quantity_added": 0,
}


def reset_report():
    for key in REPORT:
        REPORT[key] = 0


def _config_value(configuration, key, default):
    if configuration is None:
        return default
    getter = getattr(configuration, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(configuration, key, default)


def _standard_configuration(configuration):
    """Require exact standard integer timing/capacity values; malformed values fail closed."""
    for key, expected in _STANDARD_CONFIG.items():
        actual = _config_value(configuration, key, expected)
        if type(actual) is not int or actual != expected:
            return False
    return True


def _strict_positive_int(value):
    return value if type(value) is int and value > 0 else None


def apply_floor_liquidation(observation, configuration, action):
    """Append safe $1 floor sales at step 717 without altering any parent market row."""
    REPORT["calls"] += 1
    if not ENABLED:
        return action
    if not isinstance(action, dict):
        return action
    if not isinstance(observation, dict):
        return action
    if observation.get("step") != E5_STEP or type(observation.get("step")) is not int:
        return action
    if not _standard_configuration(configuration):
        return action

    raw_market = action.get("market")
    if not isinstance(raw_market, list) or len(raw_market) >= r04.MAX_ORDERS:
        return action

    try:
        view = r04.FarmView(observation)
        stock = r04.projected_shed(action, view)
    except (KeyError, TypeError, ValueError, IndexError):
        return action

    prices = getattr(view, "prices", None)
    if not isinstance(prices, dict):
        return action

    already_selling = {item: 0 for item in SAFE_ITEMS}
    for order in raw_market:
        if not isinstance(order, list) or not order:
            continue
        if order[0] != "SELL" or len(order) < 2 or order[1] not in already_selling:
            continue
        if len(order) < 3:
            return action
        qty = _strict_positive_int(order[2])
        if qty is None:
            return action
        already_selling[order[1]] += qty

    room = r04.MAX_ORDERS - len(raw_market)
    extra = []
    for item in SAFE_ITEMS:
        if room <= 0:
            break
        price = prices.get(item)
        if type(price) is not int or price != 1:
            continue
        available = stock.get(item, 0)
        if type(available) is not int or available <= 0:
            continue
        quantity = available - already_selling[item]
        if quantity <= 0:
            continue
        extra.append(["SELL", item, quantity])
        room -= 1

    if not extra:
        return action

    result = dict(action)
    result["market"] = list(raw_market) + extra
    REPORT["activations"] += 1
    REPORT["rows_added"] += len(extra)
    REPORT["quantity_added"] += sum(row[2] for row in extra)
    return result


def install(enabled=True):
    """Arm the experiment on top of exact shipped V3.1 R04 defaults."""
    global ENABLED
    ENABLED = bool(enabled)
    base = r04.install(
        horizon=8,
        opening=0,
        row_order=True,
        evening_flush=True,
        sale_fertilizer=True,
        cattle_early=True,
    )

    def agent(observation, configuration=None):
        parent = base(observation, configuration)
        return apply_floor_liquidation(observation, configuration, parent)

    return agent
