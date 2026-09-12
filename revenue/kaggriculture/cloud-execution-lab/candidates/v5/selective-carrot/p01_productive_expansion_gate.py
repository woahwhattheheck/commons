# SPDX-License-Identifier: Apache-2.0
"""Observation-only payback gate for V219's late tomato expansion.

The gate does not add a new strategy. It only decides whether the existing V219
investment is allowed to start at day 18.  It uses the authored R04 route to
price the extra Fibonacci hires, the fixed SE-land/seed spend, the policy's
bounded fertilizer reserve, the public market inventory/price curve, and an
upper bound on tomato supply already visible on the rival farm.
"""

FIXED_LAND_AND_SEED = 4500       # SE land 4000 + ten TOMATO seed at 50.
FERTILIZER_RESERVE = 700         # two bounded 10-unit buys, V219 budgets price+5 <= 35.
MAX_OWN_UNITS = 80               # ten plants * four dates * at most two units fertilized.
TERMINAL_DAY = 29


def _extra_workers(day):
    if day in (19, 20, 21, 22, 23, 25):
        return 1
    if day in (26, 27, 28):
        return 3 + int(day == 27)  # dedicated fertilizer worker only on day 27.
    return 2  # day 18, 24, 29


def route_labor_cost(native, native_day, fib):
    """Exact authored-route cost of V219's extra hands, assuming its requests execute."""
    total = 0
    for day in range(18, 30):
        planned = native_day(native, day)
        if not planned:
            raise ValueError('V219 payback gate requires a complete day 18..29 route')
        expected = max(len(action.get('hands', [])) for action in planned)
        count = _extra_workers(day)
        total += sum(fib(index) for index in range(expected, expected + count))
    return total


def rival_tomato_supply_bound(observation):
    """Public upper bound on units a visible rival TOMATO crop can still dump by day 29.

    Existing held yield is counted directly.  Every not-yet-realized production
    date is counted at the fertilized two-unit maximum.  This deliberately
    overstates rival supply and never inspects private shed/inventory state.
    """
    player = int(observation['player'])
    farms = observation.get('farms') or []
    if len(farms) < 2:
        return 0
    rival = farms[1 - player]
    day = int(observation['step']) // 24
    units = 0
    for row in rival.get('tiles', []):
        for tile in row:
            if not isinstance(tile, dict) or tile.get('crop') != 'TOMATO':
                continue
            units += max(0, int(tile.get('yield_units', 0) or 0))
            planted = tile.get('planted_day')
            if not isinstance(planted, int):
                # Unknown age: four future production dates at two units each.
                units += 8
                continue
            for production_day in range(planted + 8, planted + 12):
                if day < production_day <= TERMINAL_DAY:
                    units += 2
    return units


def evaluate(observation, native, native_day, fib, market_price):
    """Return a transparent payback record; decision=None preserves parent behavior.

    The revenue projection intentionally gives the candidate no credit for
    future town consumption or future shop unlocks.  Visible rival supply is
    inserted before our own 80-unit sale stream.  The projection is only used
    on the pinned default curve: if the current observed quote does not match
    that curve, the caller should leave V219 unchanged.
    """
    market = observation.get('market') or {}
    prices = market.get('prices') or {}
    inventory = market.get('inventory') or {}
    if 'TOMATO' not in prices or 'TOMATO' not in inventory:
        return {'decision': None, 'reason': 'missing_market'}
    current_inventory = int(inventory['TOMATO'])
    observed_quote = int(prices['TOMATO'])
    if int(market_price('TOMATO', current_inventory)) != observed_quote:
        return {'decision': None, 'reason': 'custom_market_curve'}

    labor = route_labor_cost(native, native_day, fib)
    rival_supply = rival_tomato_supply_bound(observation)
    start_inventory = current_inventory + rival_supply
    projected_gross = sum(int(market_price('TOMATO', start_inventory + sold))
                          for sold in range(MAX_OWN_UNITS))
    total_cost = FIXED_LAND_AND_SEED + FERTILIZER_RESERVE + labor
    decision = projected_gross >= total_cost
    return {
        'decision': decision,
        'reason': 'break_even' if decision else 'negative_payback',
        'labor_cost': labor,
        'fixed_cost': FIXED_LAND_AND_SEED,
        'fertilizer_reserve': FERTILIZER_RESERVE,
        'total_cost': total_cost,
        'max_own_units': MAX_OWN_UNITS,
        'visible_rival_supply_bound': rival_supply,
        'projected_gross': projected_gross,
        'projected_headroom': projected_gross - total_cost,
        'observed_tomato_quote': observed_quote,
        'starting_market_inventory': current_inventory,
    }
