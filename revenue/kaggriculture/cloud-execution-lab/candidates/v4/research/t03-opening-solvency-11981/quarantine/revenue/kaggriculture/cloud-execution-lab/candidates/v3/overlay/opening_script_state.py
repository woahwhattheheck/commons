# SPDX-License-Identifier: Apache-2.0
"""Fail-closed public-state parsing and fixed opening costs."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

from opening_script_data import LAND_COSTS


def integer(value: Any, *, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not an integer quantity")
    number = int(value)
    if number != value or number < minimum:
        raise ValueError("invalid integer quantity")
    return number


def number(value: Any, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not a numeric amount")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ValueError("invalid finite non-negative number")
    return result


def fibonacci_hire(index: int) -> int:
    """Engine hire sequence 1, 1, 2, 3, 5, ... at zero-based ``index``."""
    if index <= 1:
        return 1
    a, b = 1, 1
    for _ in range(2, index + 1):
        a, b = b, a + b
    return b


def own_farm(obs: Mapping[str, Any]) -> Mapping[str, Any]:
    farms = obs.get("farms") or []
    player = integer(obs.get("player", 0), minimum=0)
    if (not isinstance(farms, Sequence) or isinstance(farms, (str, bytes))
            or player >= len(farms)):
        raise ValueError("bad player/farms")
    farm = farms[player]
    if not isinstance(farm, Mapping):
        raise ValueError("bad own farm")
    return farm


def land_cost(
    farm: Mapping[str, Any],
    config: Mapping[str, Any],
    queued_land: int = 0,
) -> float:
    prices = config.get("opening_land_costs", LAND_COSTS)
    if not isinstance(prices, Sequence) or isinstance(prices, (str, bytes)):
        raise ValueError("bad land price sequence")
    unlocked = farm.get("unlocked_quadrants") or []
    if not isinstance(unlocked, Sequence) or isinstance(unlocked, (str, bytes)):
        raise ValueError("bad unlocked quadrants")
    index = max(0, len(unlocked) - 1) + queued_land
    if index >= len(prices):
        raise ValueError("no remaining land purchase")
    return number(prices[index])
