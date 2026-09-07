# SPDX-License-Identifier: Apache-2.0
"""Selected-action SELL transform with caller-owned production projections.

No parent controller is imported, constructed, called, or advanced here.
Pending producer lots constrain capacity only; they never become sale stock.
The accepted standalone scheduler.py remains a separate frozen policy.
"""
from __future__ import annotations

import copy
import math
import mechanics as m
from selected_sell_core import absorption, optimize_lot

PRODUCTS = tuple(p for p in m.PRODUCTS if p not in ('WHEAT', 'FERTILIZER'))
PHASES = {'before_market': 0, 'after_market': 1}


def absolute_step(obs, config):
    value = obs.get('step')
    return int(value if value is not None else
               int(obs['day']) * int(config.get('turnsPerDay', 24)) + int(obs['hour']))


def _count(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or int(value) != value:
        raise ValueError('Expected an integer count')
    return int(value)


def _orders(action):
    value = action.get('market', [])
    if not isinstance(value, list):
        raise ValueError('Market orders must be a list')
    return value


def _sell(order, item=None):
    return bool(isinstance(order, list) and len(order) >= 3 and order[0] == 'SELL'
                and (item is None or order[1] == item))


def replace_sales(orders, item, quantity, available, max_orders, reserved=()):
    """Keep economic prefixes and all original positions; append only at end.

    A SELL preceding any non-SELL order remains byte-identical. This preserves
    its actual funding and space contribution to inherited purchases/hiring.
    A reserved SELL position is left to the caller's selected action.
    """
    out = copy.deepcopy(orders)
    last_economic = max((i for i, o in enumerate(orders)
                         if o and not _sell(o)), default=-1)
    if any(i in reserved and _sell(o, item) for i, o in enumerate(orders)):
        return None
    left, stock = int(quantity), int(available)
    for i, order in enumerate(orders):
        if not _sell(order, item):
            continue
        request = max(0, _count(order[2]))
        if i <= last_economic:
            filled = min(stock, request)
            if left < filled:
                return None
        else:
            filled = min(stock, request, left)
            out[i] = ['SELL', item, filled] if filled else []
        stock -= filled
        left -= filled
    if left:
        if left > stock or len(out) >= max_orders or len(out) in reserved:
            return None
        out.append(['SELL', item, left])
    return out


def normalize_selected(action, shed, reserved_stock):
    """Express engine-clamped fills with one shared post-unit stock budget."""
    result = copy.deepcopy(action)
    physical = dict(shed)
    available = {p: max(0, q - reserved_stock.get(p, 0)) for p, q in shed.items()}
    orders = _orders(result)
    last_economic = max((i for i, order in enumerate(orders) if order and not _sell(order)), default=-1)
    for i, order in enumerate(orders):
        if not _sell(order) or order[1] not in PRODUCTS:
            continue
        item, request = order[1], max(0, _count(order[2]))
        baseline_fill = min(request, physical.get(item, 0))
        fill = min(request, available.get(item, 0))
        if i <= last_economic and fill != baseline_fill:
            raise ValueError('Stock reservation conflicts with an inherited economic prefix')
        physical[item] = physical.get(item, 0) - baseline_fill
        available[item] = available.get(item, 0) - fill
        orders[i] = ['SELL', item, fill] if fill else []
    return result


class ProjectionLedger:
    """Conditional lossless stock flows supplied by the selected producer.

    stock_events are signed non-market shed changes, including observed carried
    goods' actual DROP/EOD deposits. capacity_events are separate committed,
    unrealized whole-lot obligations. Neither projection executes farm actions.
    """
    def __init__(self, obs, config, base, shed, projection, contract, reservations, horizon):
        self.obs, self.config, self.base = obs, config, base
        self.now = absolute_step(obs, config)
        self.last = int(config.get('episodeSteps', 720)) - 2
        self.end = _count(projection['end_step'])
        if _count(projection['observed_step']) != self.now:
            raise ValueError('Projection is for a different observation')
        if not self.now <= self.end <= min(self.last, self.now + horizon):
            raise ValueError('Projection must cover a bounded actionable horizon')
        self.shed = {p: _count(q) for p, q in shed.items()}
        if any(q < 0 for q in self.shed.values()):
            raise ValueError('Negative post-unit stock')
        self.capacity = int(config.get('shedCapacity', 100))
        self.max_orders = int(config.get('maxMarketOrdersPerTurn', 10))
        self.future = {int(t): copy.deepcopy(orders) for t, orders in projection['future_market'].items()}
        self.future[self.now] = copy.deepcopy(_orders(base))
        self.events = {}
        for event in projection['stock_events']:
            t, phase = _count(event['step']), event['phase']
            if phase not in PHASES or t < self.now:
                raise ValueError('Invalid stock-event phase or date')
            if t == self.now and phase == 'before_market':
                raise ValueError('Current unit arrivals already belong in post_unit_shed')
            delta = _count(event['quantity_delta'])
            self.events.setdefault((t, phase), []).append((event['product'], delta))
        self.pending = []
        seen = {}
        if contract is not None:
            if int(contract.get('observed_step', self.now)) != self.now:
                raise ValueError('Arrival contract is for a different observation')
            for event in contract.get('capacity_events', []):
                # The T08 contract already subtracts observed carried realization.
                key = (event['owner'], event['errand_id'])
                if key in seen:
                    if seen[key] != event:
                        raise ValueError('Conflicting committed errand rows')
                    continue
                seen[key] = event
                if event.get('guaranteed_stock_units', 0) != 0 or event.get('contingent') is not True:
                    raise ValueError('Expected a contingent committed capacity event')
                if event['phase'] not in PHASES or _count(event['step']) < self.now:
                    raise ValueError('Invalid committed event phase or date')
                units = _count(event['pending_capacity_units'])
                if units < 0 or units > _count(event['units_total']):
                    raise ValueError('Invalid whole-lot pending quantity')
                self.pending.append((_count(event['step']), event['phase'], units))
        reservations = reservations or {}
        self.stock_min = {p: _count(q) for p, q in reservations.get('stock', {}).items()}
        self.cash_min = {}
        for event in reservations.get('cash', []):
            key = (_count(eve... (truncated)