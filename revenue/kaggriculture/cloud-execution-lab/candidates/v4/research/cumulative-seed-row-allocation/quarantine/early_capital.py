# SPDX-License-Identifier: Apache-2.0
# This module orders actions only inside the Kaggle Kaggriculture simulation game.
"""Horizon-aware same-queue capital investment ordering.

Improves one canonical TITAN. It never invents purchases, never changes worker
actions, never credits future or rival sales, and never inspects private rival
state. Only current-queue SELL rows certified to commit at least one unit after
the exact selected unit stage may fund later capital indices.

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


def _market_limit(config):
    """Return the executable raw-market prefix length, or None.

    The interpreter executes at least one row even when the configured limit is
    zero. Reject non-integral configuration rather than letting an optional
    ordering transform reinterpret the action grammar.
    """
    limit = config.get('maxMarketOrdersPerTurn', 10)
    if isinstance(limit, bool) or not isinstance(limit, int):
        return None
    return max(1, limit)


def _qty(order):
    if not isinstance(order, list) or len(order) < 3:
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
        hands = row.get('hands', [])
        if not isinstance(hands, list):
            hands = []
        acts = [row.get('farmer', ['PASS']), *hands]
        for action in acts:
            if isinstance(action, list) and len(action) > 1 and action[0] == 'PLANT':
                crop = action[1]
                demand[crop] = demand.get(crop, 0) + 1

    add(selected)
    if route:
        for t in range(now + 1, min(end + 1, len(route))):
            add(route[t])
    return demand


def _active_order_supported(order, mechanics):
    """Whether this row is safe for an optional reordering transform to parse."""
    if not isinstance(order, list) or not order:
        return False
    op = order[0]
    if op not in KNOWN:
        return False
    if op in ('HIRE', 'BUY_LAND', 'PASS'):
        return True
    if len(order) < 3:
        return False
    try:
        item = order[1]
        if op == 'SELL':
            return item in mechanics.PRODUCTS
        if op == 'BUY_SEED':
            return item in mechanics.CROPS
        if op == 'BUY_ANIMAL':
            return item in mechanics.ANIMALS
        if op == 'BUY_PRODUCT':
            return item in ('WHEAT', 'FERTILIZER')
    except (AttributeError, TypeError):
        return False
    return False


def _project_post_unit_private(mechanics, observation, configuration, selected, now):
    """Run the exact extracted deterministic unit stage on private copies.

    Returns ``None`` on any malformed input or source mismatch. Optional capital
    ordering must never guess stock that the official market stage cannot see.
    """
    apply_unit = getattr(mechanics, '_apply_unit_action', None)
    if not callable(apply_unit):
        return None
    try:
        player = int(observation.get('player', 0))
        farms = observation.get('farms')
        if not isinstance(farms, (list, tuple)) or not (0 <= player < len(farms)):
            return None
        farm = deepcopy(farms[player])
        private = deepcopy(observation.get('private'))
        if not isinstance(farm, dict) or not isinstance(private, dict):
            return None
        if not isinstance(farm.get('tiles'), list):
            return None
        shed = private.get('shed')
        seeds = private.get('seeds')
        inventories = private.get('inventories')
        if not isinstance(shed, dict) or not isinstance(seeds, dict) or not isinstance(inventories, list):
            return None

        farmer_action = selected.get('farmer', ['PASS'])
        hands_actions = selected.get('hands', [])
        if not isinstance(hands_actions, list):
            hands_actions = []
        unit_actions = [farmer_action, *hands_actions]

        plant_demand = {}
        for action in unit_actions:
            if isinstance(action, list) and len(action) >= 2 and action[0] == 'PLANT':
                crop = action[1]
                plant_demand[crop] = plant_demand.get(crop, 0) + 1
        blocked = {crop for crop, count in plant_demand.items()
                   if count > seeds.get(crop, 0)}

        turns_per_day = max(1, int(configuration.get('turnsPerDay', 24)))
        board_size = int(configuration.get('boardSize', 10))
        shed_capacity = int(configuration.get('shedCapacity', 100))
        day = now // turns_per_day
        for index, action in enumerate(unit_actions):
            allowed = (['PASS'] if isinstance(action, list) and len(action) >= 2
                       and action[0] == 'PLANT' and action[1] in blocked else action)
            apply_unit(farm, private, index, allowed, board_size, day,
                       turns_per_day, shed_capacity)

        post_shed = private.get('shed')
        if not isinstance(post_shed, dict):
            return None
        products = getattr(mechanics, 'PRODUCTS', None)
        if not isinstance(products, (list, tuple)):
            return None
        for item in products:
            quantity = post_shed.get(item, 0)
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
                return None
        return private
    except (AttributeError, IndexError, KeyError, OverflowError, TypeError, ValueError):
        return None


def _certified_funding(active, mechanics, post_private):
    """Allocate post-unit shed stock to SELL rows in their original order.

    Each returned row index is guaranteed to commit at least one unit after the
    stable FUNDING partition. The allocated unit counts prevent two SELL rows
    from claiming the same private stock.
    """
    products = tuple(mechanics.PRODUCTS)
    shed = post_private['shed']
    remaining = {item: int(shed.get(item, 0)) for item in products}
    funding = set()
    units = {}
    for index, order in enumerate(active):
        if not isinstance(order, list) or len(order) < 3 or order[0] != 'SELL':
            continue
        item = order[1]
        quantity = _qty(order)
        available = remaining.get(item, 0)
        committed = min(quantity, available)
        if committed <= 0:
            continue
        funding.add(index)
        units[index] = committed
        remaining[item] = available - committed
    return funding, units


def _operating_seed_rows(active, mechanics, plant_demand, seeds_held):
    """Select an executable whole-row cover for represented seed deficits.

    A market row is indivisible for ordering: once moved ahead of capital, the
    official interpreter attempts its full positive quantity before advancing.
    Therefore a row may claim OPERATING priority only when every requested unit
    fits inside the represented deficit. For each crop, choose the subset of
    positive rows with maximum total quantity not exceeding that deficit;
    lexicographically earliest authored indices break ties. This maximizes exact
    demand coverage without splitting, editing, inventing, or overbuying rows.
    """
    remaining = {}
    rows_by_crop = {}
    for crop, count in plant_demand.items():
        if crop not in mechanics.CROPS:
            continue
        need = max(0, int(count) - int(seeds_held.get(crop, 0)))
        remaining[crop] = need
        rows_by_crop[crop] = []

    for index, order in enumerate(active):
        if (not isinstance(order, list) or len(order) < 3
                or order[0] != 'BUY_SEED'):
            continue
        crop = order[1]
        if crop not in rows_by_crop:
            continue
        quantity = _qty(order)
        if quantity > 0:
            rows_by_crop[crop].append((index, quantity))

    operating = set()
    allocations = []
    for crop in sorted(rows_by_crop):
        need = remaining[crop]
        # total -> lexicographically earliest tuple of row indices producing it.
        choices = {0: ()}
        quantities = {}
        for index, quantity in rows_by_crop[crop]:
            quantities[index] = quantity
            updated = dict(choices)
            for total, indices in choices.items():
                candidate_total = total + quantity
                if candidate_total > need:
                    continue
                candidate = indices + (index,)
                incumbent = updated.get(candidate_total)
                if incumbent is None or candidate < incumbent:
                    updated[candidate_total] = candidate
            choices = updated

        covered = max(choices)
        selected_indices = choices[covered]
        for index in selected_indices:
            quantity = quantities[index]
            operating.add(index)
            allocations.append({
                'index': index,
                'crop': crop,
                'requested': quantity,
                'allocated': quantity,
            })
        remaining[crop] = need - covered

    allocations.sort(key=lambda row: row['index'])
    return operating, allocations, remaining


def _capital_admitted(order, mechanics, remaining, day):
    if not isinstance(order, list) or not order:
        return False
    if day > EARLY_DAY_LIMIT:
        return False
    op = order[0]
    if op == 'BUY_LAND':
        return remaining >= PAYBACK_DAYS['LAND']
    if (op == 'BUY_ANIMAL' and len(order) > 2 and order[1] in mechanics.ANIMALS
            and _qty(order) > 0):
        return remaining >= PAYBACK_DAYS[order[1]]
    return False


def _rank(order, index, funding, seed_operating, mechanics, remaining, day):
    if not order:
        return REST
    op = order[0]
    if op == 'SELL':
        return FUNDING if index in funding else REST
    if op == 'HIRE':
        return OPERATING
    if op == 'BUY_SEED' and len(order) > 2 and order[1] in mechanics.CROPS:
        return OPERATING if index in seed_operating else REST
    if _capital_admitted(order, mechanics, remaining, day):
        return CAPITAL
    return REST


def order_early_capital(mechanics, observation, configuration, selected, route, decisions=()):
    """Reorder only the executable prefix of the current market tape.

    Purchases are never dropped or invented. Farmer/hands, market length, the
    multiset of active orders, and every capped suffix row remain unchanged.
    """
    report = {'changed': False, 'reason': 'init', 'moved': 0, 'reserved': 0,
              'reduced': [], 'revision': 'v6-whole-seed-rows'}
    if not isinstance(selected, dict):
        report['reason'] = 'no_action'
        return selected, report
    raw_market = selected.get('market')
    if raw_market is None:
        raw_market = []
    if not isinstance(raw_market, list):
        report['reason'] = 'unsupported_market'
        return selected, report
    market = list(raw_market)
    if not market:
        report['reason'] = 'empty_market'
        return selected, report
    limit = _market_limit(configuration)
    if limit is None:
        report['reason'] = 'unsupported_market_limit'
        return selected, report
    active_count = min(limit, len(market))
    active = market[:active_count]
    suffix = market[active_count:]
    report.update(active_limit=limit, active_rows=active_count,
                  suffix_rows=len(suffix))

    try:
        now = int(observation.get('step') if observation.get('step') is not None
                  else int(observation['day']) * _turns_per_day(configuration)
                  + int(observation['hour']))
        last = _last_step(configuration)
        turns_per_day = _turns_per_day(configuration)
    except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
        report['reason'] = 'unsupported_time'
        return selected, report
    if turns_per_day <= 0:
        report['reason'] = 'unsupported_time'
        return selected, report
    if now >= last:
        report['reason'] = 'terminal_window'
        return selected, report
    if not all(_active_order_supported(order, mechanics) for order in active):
        report['reason'] = 'unsupported_active_order'
        return selected, report

    post_private = _project_post_unit_private(
        mechanics, observation, configuration, selected, now)
    if post_private is None:
        report['reason'] = 'post_unit_projection_failed'
        return selected, report
    funding, funding_units = _certified_funding(active, mechanics, post_private)
    report.update(
        certified_funding_rows=sorted(funding),
        certified_funding_units=[
            {'index': index, 'item': active[index][1], 'units': funding_units[index]}
            for index in sorted(funding)
        ],
    )

    day = now // turns_per_day
    remaining = _remaining_days(now, configuration)
    seeds_held = dict(post_private.get('seeds') or {})
    try:
        horizon = _horizon_end(now, configuration, decisions)
        # The current unit stage already ran in post_private; only future route
        # PLANT actions may still consume the post-unit seed balance.
        plants = _plant_demand(None, route, now, horizon)
        seed_operating, seed_allocations, unmet_seed_demand = _operating_seed_rows(
            active, mechanics, plants, seeds_held)
        ranks = [
            _rank(order, index, funding, seed_operating, mechanics, remaining, day)
            for index, order in enumerate(active)
        ]
    except (AttributeError, IndexError, KeyError, OverflowError, TypeError, ValueError):
        report['reason'] = 'ranking_failed'
        return selected, report
    report.update(
        operating_seed_rows=sorted(seed_operating),
        seed_allocations=seed_allocations,
        unmet_seed_demand={
            crop: count for crop, count in sorted(unmet_seed_demand.items()) if count > 0
        },
    )
    if CAPITAL not in ranks:
        report['reason'] = 'no_admitted_capital'
        return selected, report

    indexed = list(enumerate(active))
    ordered = sorted(indexed, key=lambda item: (ranks[item[0]], item[0]))
    reordered_active = [order for _, order in ordered]
    reordered = reordered_active + suffix
    moved = sum(1 for old, new in zip(active, reordered_active) if old != new)
    if reordered_active == active:
        report.update(reason='already_ordered', moved=0, horizon_end=horizon,
                      remaining_days=remaining)
        return selected, report
    result = deepcopy(selected)
    result['market'] = deepcopy(reordered)
    report.update(changed=True, reason='ordered', moved=moved, reserved=0,
                  reduced=[], horizon_end=horizon, remaining_days=remaining)
    return result, report
