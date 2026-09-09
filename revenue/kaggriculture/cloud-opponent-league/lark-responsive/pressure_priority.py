"""Observation-only SELL-lot pressure opponent; not a canonical-policy patch.

The same-sized rival lot is an explicit proxy, never observed hidden inventory.
The injected quote function must be the pinned engine's pure public price curve.
Contiguous SELL blocks may reorder. A wholly sale-only executable prefix may
also compact known empty slots; parent quantities and production remain intact.
"""
from __future__ import annotations

import copy
import math
import time
from collections.abc import Callable, Mapping
from typing import Any

from sell_priority import PRODUCTS, _quote

PriceFunction = Callable[[str, int, Mapping | None], int | float]
MAX_SCORING_UNITS = 256
MAX_SCORING_ORDERS = 64
SALE_ONLY_GOODS = frozenset(("CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL"))


def compact_sale_only_prefix(orders: list, end: int, market: Mapping,
                             configuration: Mapping, quote: PriceFunction) -> list:
    """Move sales across known empty slots in a wholly sale-only prefix.

    Relative positive-sale order, quantities, row length and the non-executable
    suffix stay intact. Buyable operating inputs and every economic/unknown
    order decline compaction. This is a current-turn ordering rule: it does not
    project future purchases, crops, or opponent policy responses.

    With no intra-market town consumption or purchases of these goods, moving
    an own sale earlier crosses only rival sales. A nonincreasing price curve
    weakly improves the changed commodity's own-minus-rival sale receipts,
    including paired quotes and the floor. This is not a full-game guarantee.
    """
    prefix = orders[:end]; positive = []; empty = []; totals = {}
    cfg_capacity = configuration.get('shedCapacity', 100)
    if isinstance(cfg_capacity, bool) or cfg_capacity != 100:
        return orders
    for order in prefix:
        if order == []:
            empty.append(order); continue
        if not isinstance(order, list) or len(order) != 3 or order[0] != 'SELL':
            return orders
        item, quantity = order[1:]
        if (not isinstance(item, str) or item not in PRODUCTS
                or isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0):
            return orders
        if quantity == 0:
            empty.append(order); continue
        if item not in SALE_ONLY_GOODS:
            return orders
        positive.append(order); totals[item] = totals.get(item, 0) + quantity
    candidate = positive + empty
    if not positive or not empty or candidate == prefix or sum(totals.values()) > cfg_capacity:
        return orders
    prices = market.get('prices', {}); inventories = market.get('inventory', {})
    params = market.get('params')
    if (not isinstance(prices, Mapping) or not isinstance(inventories, Mapping)
            or (params is not None and not isinstance(params, Mapping))):
        return orders
    exposed = False
    try:
        for item, quantity in totals.items():
            inventory = inventories.get(item)
            if isinstance(inventory, bool) or not isinstance(inventory, int):
                return orders
            visible = prices.get(item)
            if (isinstance(visible, bool) or not isinstance(visible, (int, float))
                    or not math.isfinite(visible) or visible < 1):
                return orders
            curve = [quote(item, inventory + k, params)
                     for k in range(quantity + cfg_capacity + 1)]
            if any(isinstance(p, bool) or not isinstance(p, (int, float))
                   or not math.isfinite(p) or p < 1 for p in curve):
                return orders
            if curve[0] != visible or any(a < b for a, b in zip(curve, curve[1:])):
                return orders
            exposed |= curve[0] > curve[-1]
    except (ArithmeticError, LookupError, TypeError, ValueError):
        return orders
    if not exposed:
        return orders
    return candidate + orders[end:]


def lot_pressure(order: Any, market: Mapping, quote: PriceFunction,
                 rival_quantity: int | None = None) -> float | None:
    """Return public-flow delay loss, or None when the order is an opaque barrier.

    For own requested quantity ``n`` at public inventory ``I``, compare the own
    receipt now against the same own lot after ``rival_quantity`` public units.
    When ``rival_quantity`` is omitted, retain the historical same-sized ``n``
    rival lot exactly as the explicit fallback/proxy stress.  A supplied zero is
    a real zero-flow scenario.  Supplied quantities are public scenario inputs,
    never inferred private stock or future sales.

    Current quote consistency is required. Above bounded scoring limits, retain
    the order in place instead of silently approximating either quantity.
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
    if rival_quantity is None:
        rival_n = n
    else:
        if (isinstance(rival_quantity, bool) or not isinstance(rival_quantity, int)
                or rival_quantity < 0 or rival_quantity > MAX_SCORING_UNITS):
            return None
        rival_n = rival_quantity
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
        delayed = sum(checked(stock + rival_n + k) for k in range(n))
    except (ArithmeticError, LookupError, TypeError, ValueError):
        return None
    # Negative deterioration is not urgency. Equal scores keep parent order.
    return max(0., ahead - delayed)


def transform(action: dict, observation: Mapping,
              configuration: Mapping | None = None, *, quote: PriceFunction,
              rival_supply: Mapping[str, int] | None = None) -> dict:
    """Sort contiguous supported SELL lots by public rival-flow delay exposure.

    ``rival_supply`` is an optional product->public-quantity scenario.  Missing
    product keys retain the historical same-sized proxy for that product; an
    explicit zero means no rival flow.  Malformed supplied values are barriers,
    so ambiguous data cannot silently turn into invented hidden inventory.

    Preserve all orders, quantities, duplicate lots, economic barriers,
    executable-prefix boundaries and unit instructions. Known empty slots can
    move only inside a wholly eligible sale-only prefix. Economic feedback can
    still change later parent choices; this is not a global optimality claim.
    """
    if not isinstance(action, dict) or not isinstance(action.get('market', []), list):
        raise ValueError('parent policy must return an object with a market list')
    result = copy.deepcopy(action)
    market = observation.get('market', {}) if isinstance(observation, Mapping) else {}
    if not isinstance(market, Mapping):
        return result
    if rival_supply is not None and not isinstance(rival_supply, Mapping):
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

    def supplied_quantity(order: Any) -> int | None:
        if rival_supply is None or not isinstance(order, list) or len(order) != 3:
            return None
        item = order[1]
        if item not in rival_supply:
            return None
        return rival_supply[item]

    scores = [lot_pressure(order, market, quote, supplied_quantity(order))
              for order in orders[:end]]
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
    result['market'] = compact_sale_only_prefix(orders, end, market, cfg, quote)
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
