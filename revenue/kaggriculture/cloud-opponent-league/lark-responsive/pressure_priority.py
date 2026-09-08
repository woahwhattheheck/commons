"""Observation-only SELL-lot pressure opponent; not a canonical-policy patch.

The same-sized rival lot is an explicit proxy, never observed hidden inventory.
The injected quote function must be the pinned engine's pure public price curve.
Only adjacent SELL orders move; parent quantities and production remain intact.
"""
from __future__ import annotations

import copy
import math
import time
from collections.abc import Callable, Mapping
from typing import Any

from sell_priority import _quote

PriceFunction = Callable[[str, int, Mapping | None], int | float]
MAX_SCORING_UNITS = 256
MAX_SCORING_ORDERS = 64


def lot_pressure(order: Any, market: Mapping, quote: PriceFunction) -> float | None:
    """Return same-lot delay loss, or None when the order is an opaque barrier.

    For own requested quantity n at public inventory I, compare sum price(I+k)
    with sum price(I+n+k), k=0..n-1. The hypothetical rival n is deliberately
    the parent's requested lot size, not inferred private stock or future sales.
    Current quote consistency is required. Above the bounded scoring limits,
    retain the order in place instead of silently approximating its quantity.
    """
    prices, inventory = market.get('prices', {}), market.get('inventory', {})
    if not isinstance(prices, Mapping) or not isinstance(inventory, Mapping):
        return None
    visible = _quote(order, prices)
    if visible is None:
        return None
    item, n = order[1], int(order[2])
    if n > MAX_SCORING_UNITS:
        return None
    stock = inventory.get(item)
    if isinstance(stock, bool) or not isinstance(stock, int):
        return None
    params = market.get('params')
    if params is not None and not isinstance(params, Mapping):
        return None

    def checked(at: int) -> float:
        value = quote(item, at, params)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('non-numeric public quote')
        if not math.isfinite(value) or value < 1:
            raise ValueError('non-finite or below-floor public quote')
        return float(value)

    try:
        if checked(stock) != visible:
            return None
        ahead = sum(checked(stock + k) for k in range(n))
        delayed = sum(checked(stock + n + k) for k in range(n))
    except (ArithmeticError, LookupError, TypeError, ValueError):
        return None
    # Negative deterioration is not urgency. Equal scores keep parent order.
    return max(0., ahead - delayed)


def transform(action: dict, observation: Mapping,
              configuration: Mapping | None = None, *, quote: PriceFunction) -> dict:
    """Sort contiguous supported SELL lots by public same-lot delay exposure.

    Preserve all orders, quantities, duplicate orders, non-SELL positions,
    executable-prefix boundaries and unit instructions. Economic feedback can
    still change later parent choices; this is not a global optimality claim.
    """
    if not isinstance(action, dict) or not isinstance(action.get('market', []), list):
        raise ValueError('parent policy must return an object with a market list')
    result = copy.deepcopy(action)
    market = observation.get('market', {}) if isinstance(observation, Mapping) else {}
    if not isinstance(market, Mapping):
        return result
    cfg = configuration if isinstance(configuration, Mapping) else {}
    try:
        limit = max(1, int(cfg.get('maxMarketOrdersPerTurn', 10)))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('invalid maxMarketOrdersPerTurn') from exc
    orders = result.get('market', [])
    end = min(len(orders), limit)
    if end > MAX_SCORING_ORDERS:
        return result
    scores = [lot_pressure(order, market, quote) for order in orders[:end]]
    start = 0
    while start < end:
        if scores[start] is None:
            start += 1
            continue
        stop = start + 1
        while stop < end and scores[stop] is not None:
            stop += 1
        ranked = sorted(zip(orders[start:stop], scores[start:stop]), key=lambda p: -p[1])
        orders[start:stop] = [order for order, _ in ranked]
        start = stop
    return result


def actor_class(base: type, quote: PriceFunction) -> type:
    """Compose with existing process-isolated Actor; use |supply-pressure.

    The price callback operates only on the public inventory and market params
    passed by transform. It must not read the evolving engine state or rivals.
    Parent RPC plus transform share the original supplied action deadline.
    """
    class PressurePriorityActor(base):
        def __init__(self, spec: str, *args: Any, **kwargs: Any):
            suffix = '|supply-pressure'
            self.pressure_priority = spec.endswith(suffix)
            parent = spec[:-len(suffix)] if self.pressure_priority else spec
            super().__init__(parent, *args, **kwargs)
            self.stats['pressure_priority_enabled'] = self.pressure_priority
            self.stats['pressure_priority_changed_turns'] = 0
            self.stats['pressure_priority_transform_seconds'] = []
            self.stats['pressure_priority_total_seconds'] = []

        def act(self, observation: dict, configuration: Any, timeout: float):
            entered = time.perf_counter()
            response = super().act(observation, configuration, timeout)
            if not self.pressure_priority or response.get('kind') != 'action':
                return response
            started = time.perf_counter()
            result = transform(response['action'], observation, configuration, quote=quote)
            duration = time.perf_counter() - started
            self.stats['pressure_priority_transform_seconds'].append(duration)
            if result != response['action']:
                self.stats['pressure_priority_changed_turns'] += 1
            total = time.perf_counter() - entered
            self.stats['pressure_priority_total_seconds'].append(total)
            if total > timeout:
                return {'kind': 'timeout', 'phase': 'pressure_priority',
                        'error': 'parent RPC plus transform exceeded the supplied action deadline'}
            return dict(response, action=result)

    return PressurePriorityActor
