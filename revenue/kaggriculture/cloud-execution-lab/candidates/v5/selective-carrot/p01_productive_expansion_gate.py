# SPDX-License-Identifier: Apache-2.0
"""Observation-only payback gate for V219's late tomato expansion.

The gate does not add a new strategy. It only decides whether the existing V219
investment is allowed to start at day 18.  Its labor model follows the exact
R04 request mechanics: HIRE pricing resets each day, authored parent HIREs on
that day consume the early Fibonacci indices, and V219's appended HIREs start
only after them.  Future authored HIREs are treated as successful when costing
V219, which is a conservative upper bound on V219's incremental hire spend.
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


def _hire_count(action):
    return sum(bool(order) and order[0] == 'HIRE'
               for order in action.get('market', []))


def authored_hire_context(planned):
    """Return (hires_before_request_action, hires_in_request_action).

    `_v219_request()` can act only in offsets 0..3 and refuses while any later
    authored HIRE remains.  The engine resets `hires_today` at dawn, so only
    HIRE orders in this one day contribute to the Fibonacci index.  We model
    every authored parent HIRE as successful: if a parent HIRE actually fails,
    V219's own request either fails its worker-topology guard or starts at a
    lower Fibonacci index, so this is an upper bound on V219's added hire cost.
    """
    if not planned:
        raise ValueError('V219 payback gate requires a non-empty authored day')
    hire_offsets = [(offset, _hire_count(action))
                    for offset, action in enumerate(planned)
                    if _hire_count(action)]
    if not hire_offsets:
        return 0, 0
    last_offset, parent_hires = hire_offsets[-1]
    if last_offset > 3:
        raise ValueError('V219 cannot request before the last authored HIRE')
    prior_hires = sum(count for offset, count in hire_offsets if offset < last_offset)
    return prior_hires, parent_hires


def incremental_hire_cost(prior_hires, parent_hires, extra_hires, fib):
    """Price only V219-added HIREs after same-action parent HIREs.

    This mirrors `_v219_request()` / engine ordering: with `hires_today` equal
    to `prior_hires` on entry, parent HIREs execute first in the market list,
    then V219's first incremental worker is Fibonacci index
    `prior_hires + parent_hires`.
    """
    start = int(prior_hires) + int(parent_hires)
    count = int(extra_hires)
    if min(start, count) < 0:
        raise ValueError('HIRE counts must be non-negative')
    return sum(fib(index) for index in range(start, start + count))


def route_labor_cost(native, native_day, fib):
    """Conservative full-route upper bound on V219's incremental HIRE spend."""
    total = 0
    for day in range(18, 30):
        planned = native_day(native, day)
        if not planned:
            raise ValueError('V219 payback gate requires a complete day 18..29 route')
        prior_hires, parent_hires = authored_hire_context(planned)
        total += incremental_hire_cost(
            prior_hires, parent_hires, _extra_workers(day), fib)
    return total


def visible_rival_field_supply_bound(observation):
    """Upper bound on *visible-field* rival TOMATO units through day 29.

    Existing visible tile yield is counted directly. Every not-yet-realized
    production date is counted at the fertilized two-unit maximum. This does
    NOT claim to bound private rival shed/carried TOMATO, which is unavailable
    to the policy; the value is only an observable market-pressure adjustment.
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
                units += 8  # four possible future production dates * two units.
                continue
            for production_day in range(planted + 8, planted + 12):
                if day < production_day <= TERMINAL_DAY:
                    units += 2
    return units


def evaluate(observation, native, native_day, fib, market_price):
    """Return a transparent research admission record.

    `decision=None` preserves the parent. The projection deliberately gives no
    credit for future town consumption or future shop unlocks and applies only
    when the observed TOMATO quote matches the pinned market curve.  It is a
    conservative experiment gate, not a proof of universal profitability: the
    labor/fertilizer side is an upper-bound full-execution cost while 80 units
    is an optimistic production ceiling. Native matched games remain the
    economic authority before any activation.
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
    visible_rival_supply = visible_rival_field_supply_bound(observation)
    start_inventory = current_inventory + visible_rival_supply
    projected_gross = sum(int(market_price('TOMATO', start_inventory + sold))
                          for sold in range(MAX_OWN_UNITS))
    modeled_cost_ceiling = FIXED_LAND_AND_SEED + FERTILIZER_RESERVE + labor
    decision = projected_gross >= modeled_cost_ceiling
    return {
        'decision': decision,
        'reason': 'modeled_break_even' if decision else 'modeled_negative_headroom',
        'incremental_labor_cost_ceiling': labor,
        'fixed_cost': FIXED_LAND_AND_SEED,
        'fertilizer_reserve_ceiling': FERTILIZER_RESERVE,
        'modeled_cost_ceiling': modeled_cost_ceiling,
        'max_own_units': MAX_OWN_UNITS,
        'visible_rival_field_supply_bound': visible_rival_supply,
        'projected_gross_ceiling': projected_gross,
        'modeled_headroom': projected_gross - modeled_cost_ceiling,
        'observed_tomato_quote': observed_quote,
        'starting_market_inventory': current_inventory,
    }
