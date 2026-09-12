# SPDX-License-Identifier: Apache-2.0
"""r04_fert_warehouse: use the fertilizer market as infinite off-site storage.

MECHANICS (verified vs pinned official kaggriculture.py 2026-09-12):
- FERTILIZER MARKET_PARAMS: base=100, I0=10000, T=200, below_func='linear',
  below_target=0.4. Price hits the $1 PRICE_FLOOR at inv >= ~10499 and STAYS
  there for any larger inventory.
- FERTILIZER is excluded from TOWN_CENTER_PRODUCTS and no shop buys it, so
  market inventory is monotonically non-decreasing from player sales: once the
  floor is reached it is permanent.
- market_price(inv) == market_price(inv-1) == $1 at the floor, so SELL-all +
  later BUY_PRODUCT buyback is a ZERO-FRICTION 1-to-1 storage mechanism with
  infinite capacity. (Antigravity / commons_swarm discovery.)

POLICY (hybrid, merges Riot's revenue-timing lane with Antigravity's dump):
- Mode A (revenue): fertilizer price above REVENUE_PRICE_THRESHOLD -> SELL
  for revenue (the classic r04_fert_liquidate timing: price drifts $100->$44).
- Mode B (warehouse): shed at/over SHED_CRITICAL units and price at the $1
  floor -> SELL every fertilizer unit we hold (shed + carried). Never discard
  to the 100-cap EOD wipe while the market will take it for $1 and give it
  back for $1.
- Buyback needs no lane: normal BUY_PRODUCT FERTILIZER when the crop logic
  wants fertilizer; at the floor it costs $1.

Default OFF. OFF == base behavior exactly (this module is not even called).
"""

from __future__ import annotations

SHED_CAPACITY = 100
# Dump everything when the shed is this full and the floor is in reach.
SHED_CRITICAL = 80
# Antigravity's threshold-to-1 semantics: dump at any price <= this when the
# shed is critical. 1 == pure warehouse mode; higher == revenue blend.
DUMP_PRICE_THRESHOLD = 1
# Riot revenue path: sell for cash while quotes are still healthy.
REVENUE_PRICE_THRESHOLD = 44


def _as_int(value, default=0):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return n if n >= 0 else default


def shed_total(private, shed_capacity=SHED_CAPACITY):
    """Total units currently in the shed."""
    shed = (private or {}).get('shed') or {}
    return sum(_as_int(v) for v in shed.values())


def fertilizer_held(private):
    """All fertilizer units we hold (shed + every hand's inventory)."""
    private = private or {}
    total = _as_int((private.get('shed') or {}).get('FERTILIZER'))
    for inv in private.get('inventories') or []:
        total += _as_int((inv or {}).get('FERTILIZER'))
    return total


def warehouse_dump_orders(private, market_price, *,
                          shed_critical=SHED_CRITICAL,
                          dump_price_threshold=DUMP_PRICE_THRESHOLD):
    """SELL orders implementing Mode B (warehouse dump).

    Returns [] unless: shed is at/over `shed_critical`, the fertilizer market
    price is at/under `dump_price_threshold`, and we hold fertilizer.
    Emits one SELL order per container holding fertilizer (engines that cap
    orders/turn can split across turns; callers should bound by
    maxMarketOrdersPerTurn).
    """
    price = _as_int(market_price, 10 ** 9)
    if price > _as_int(dump_price_threshold, 1):
        return []
    if shed_total(private) < _as_int(shed_critical, SHED_CRITICAL):
        return []
    orders = []
    private = private or {}
    shed_qty = _as_int((private.get('shed') or {}).get('FERTILIZER'))
    if shed_qty > 0:
        orders.append(['SELL', 'FERTILIZER', shed_qty])
    for inv in private.get('inventories') or []:
        qty = _as_int((inv or {}).get('FERTILIZER'))
        if qty > 0:
            orders.append(['SELL', 'FERTILIZER', qty])
    return orders


def revenue_sell_quantity(private, market_price, *,
                          revenue_price_threshold=REVENUE_PRICE_THRESHOLD):
    """Mode A (revenue): fertilizer units to sell while quotes are healthy."""
    if _as_int(market_price, 0) < _as_int(revenue_price_threshold, REVENUE_PRICE_THRESHOLD):
        return 0
    return fertilizer_held(private)


def decide(private, market_price, *,
           shed_critical=SHED_CRITICAL,
           dump_price_threshold=DUMP_PRICE_THRESHOLD,
           revenue_price_threshold=REVENUE_PRICE_THRESHOLD):
    """One-shot hybrid decision. Returns {'mode', 'orders'}.

    mode is 'warehouse' | 'revenue' | 'hold'.
    """
    dump = warehouse_dump_orders(private, market_price,
                                 shed_critical=shed_critical,
                                 dump_price_threshold=dump_price_threshold)
    if dump:
        return {'mode': 'warehouse', 'orders': dump}
    qty = revenue_sell_quantity(private, market_price,
                                revenue_price_threshold=revenue_price_threshold)
    if qty > 0:
        return {'mode': 'revenue',
                'orders': [['SELL', 'FERTILIZER', qty]]}
    return {'mode': 'hold', 'orders': []}
