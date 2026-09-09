# SPDX-License-Identifier: Apache-2.0
"""Horizon-aware same-queue capital investment ordering.

Improves one canonical TITAN. It never invents purchases, never changes worker
actions, never credits future or rival sales, and never inspects private rival
state. Current-queue SELL rows already on the tape may fund later indices after
they are moved to the front; that is same-turn engine cash, not a forecast.

v1 reserved cash by reducing discretionary BUY_SEED / BUY_PRODUCT to PASS,
including cross-turn upcoming land. Official first-eight games showed that
hoard: patch day-11 cash rose while terminal score and Arlene win rate fell.
v2 is ordering only. Every original purchase stays on the tape.

Distinct from P22 terminal payback, S08 maximin ranking, E16 terminal
settlement, S02 receding-horizon MPC, and fourth-quadrant land admission.
"""
from __future__ import annotations

from copy import deepcopy

PAYBACK_DAYS = {'GOOSE': 4, 'COW': 8, 'SHEEP': 6, 'LAND': 4}
EARLY_DAY_LIMIT = 20
KNOWN = frozenset(('SELL', 'HIRE', 'BUY_LAND', 'BUY_SEED', 'BUY_ANIMAL', 'BUY_PRODUCT', 'PASS'))
FUNDING = 0
OPERATING = 1
CAPITAL = 2
REST = 3


def _last_step(config):
    return int(config.get('episodeSteps', 720)) - 2


def _turns_per_day(config):
    return int(config.get('turnsPerDay', 24))


def _remaining_days(now, config):
    last = _last_step(config)
    tpd = _turns_per_day(config)
    if tpd <= 0 or now > last:
        return 0
    return max(0, (last - now) // tpd)


def _horizon_end(now, config, decisions):
    last = _last_step(config)
    tpd = _turns_per_day(config)
    end = min(last, now + tpd)
    for checkpoint, *_ in decisions or ():
        if now < int(checkpoint) <= end:
            end = int(checkpoint)
            break
    return end


def _qty(order):
    if not order or len(order) < 3:
        return 0
    try:
        return max(0, int(order[2]))
    except (TypeError, ValueError):
        return 0


def _plant_demand(selected, route, now, end):
    demand = {}
    def add(row):
        if not isinstance(row, dict):
            return
        acts = [row.get('farmer', ['PASS']), *(row.get('hands') or [])]
        for action in acts:
            if action and action[0] == 'PLANT' and len(action) > 1:
                crop = action[1]
                demand[crop] = demand.get(crop, 0) + 1
    add(selected)
    if route:
        for t in range(now + 1, min(end + 1, len(route))):
            add(route[t])
    return demand


def _capital_admitted(order, now, remaining, day):
    if not order:
        return False
    if day > EARLY_DAY_LIMIT:
        return False
    op = order[0]
    if op == 'BUY_LAND':
        return remaining >= PAYBACK_DAYS['LAND']
    if op == 'BUY_ANIMAL' and len(order) > 2 and _qty(order) > 0:
        return remaining >= PAYBACK_DAYS.get(order[1], 8)
    return False


def _rank(order, now, remaining, day, plant_demand, seeds_held):
    if not order:
        return REST
    op = order[0]
    if op not in KNOWN:
        return None
    if op == 'SELL':
        return FUNDING
    if op == 'HIRE':
        return OPERATING
    if op == 'BUY_SEED' and len(order) > 2:
        crop = order[1]
        need = max(0, int(plant_demand.get(crop, 0)) - int(seeds_held.get(crop, 0)))
        return OPERATING if need > 0 else REST
    if _capital_admitted(order, now, remaining, day):
        return CAPITAL
    return REST


def order_early_capital(mechanics, observation, configuration, selected, route, decisions=()):
    """Reorder the current market tape. Purchases are never dropped or invented.

    Returns (action, report). Action farmer/hands are unchanged. Market length
    and the multiset of orders are unchanged; only same-queue index order.
    """
    report = {'changed': False, 'reason': 'init', 'moved': 0, 'reserved': 0,
              'reduced': [], 'revision': 'v2-order-only'}
    if not isinstance(selected, dict):
        report['reason'] = 'no_action'
        return selected, report
    market = list(selected.get('market') or [])
    if not market:
        report['reason'] = 'empty_market'
        return selected, report
    now = int(observation.get('step') if observation.get('step') is not None
              else int(observation['day']) * _turns_per_day(configuration)
              + int(observation['hour']))
    last = _last_step(configuration)
    if now >= last:
        report['reason'] = 'terminal_window'
        return selected, report
    day = now // _turns_per_day(configuration)
    remaining = _remaining_days(now, configuration)
    if any(o and o[0] not in KNOWN for o in market):
        report['reason'] = 'unknown_order'
        return selected, report
    player = int(observation['player'])
    private = observation.get('private') or {}
    seeds_held = dict(private.get('seeds') or {})
    horizon = _horizon_end(now, configuration, decisions)
    plants = _plant_demand(selected, route, now, horizon)
    ranks = []
    for order in market:
        rank = _rank(order, now, remaining, day, plants, seeds_held)
        if rank is None:
            report['reason'] = 'unknown_order'
            return selected, report
        ranks.append(rank)
    if CAPITAL not in ranks:
        report['reason'] = 'no_admitted_capital'
        return selected, report

    indexed = list(enumerate(market))
    ordered = sorted(indexed, key=lambda item: (ranks[item[0]], item[0]))
    reordered = [order for _, order in ordered]
    moved = sum(1 for old, new in zip(market, reordered) if old != new)
    if reordered == market:
        report.update(reason='already_ordered', moved=0, horizon_end=horizon,
                      remaining_days=remaining)
        return selected, report
    result = deepcopy(selected)
    result['market'] = reordered
    report.update(changed=True, reason='ordered', moved=moved, reserved=0,
                  reduced=[], horizon_end=horizon, remaining_days=remaining)
    return result, report
