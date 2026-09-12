"""r04_fert_liquidate (v2): fertilizer overflow loss-prevention.

Antigravity's $1 fertilizer warehouse, minimal safe form (credit: Antigravity).

The engine destroys any collected item that doesn't fit in the 100-cap shed
(kaggriculture.py: room = max(0, 100 - sum(shed.values())); excess is deleted).
This lane converts would-be-destroyed fertilizer into cash instead.

It ONLY acts when the shed is imminently full (>= SHED_NEAR_FULL total items)
and holds fertilizer. It dumps just enough fertilizer to bring total shed down
to SHED_TARGET, leaving headroom. It never strips buys, never sells early for
"revenue timing", never tracks market inventory, never does buyback. Pure loss
prevention: $0 (destroyed) -> $1+ (sold; at worst at the verified $1 floor).

Rationale for v2: v1's Mode A (early revenue-timing sales + buy stripping)
changed early-game cash flow and flipped major trajectory decisions, producing
chaotic +/-$35k cell swings (gate 2026-09-12). v2 is cash-flow neutral until
the moment of imminent destruction, so it cannot destabilize the base plan.

Wiring: titan_runtime._fert_liquidate_selected calls apply() with
(obs, selected, enabled, shed_stock, s1_on, max_orders); last_report() feeds
diagnostics. Default OFF. Flag: r04_fert_liquidate=true.
"""

# Shed is imminently full at this total item count; dump down to this target.
SHED_NEAR_FULL = 98
SHED_TARGET = 90

_report = {"engaged": 0, "dumped": 0}


def last_report():
    return dict(_report)


def _shed_total(shed_stock):
    try:
        return sum(int(v) for v in (shed_stock or {}).values())
    except Exception:
        return 0


def apply(obs, selected, enabled=True, shed_stock=None, s1_on=False,
          max_orders=10):
    """Prepend a SELL row dumping fertilizer overflow. Returns selected."""
    if not enabled:
        return selected
    if not isinstance(selected, list):
        return selected
    try:
        max_orders = int(max_orders or 10)
    except Exception:
        max_orders = 10
    if len(selected) >= max_orders:
        return selected

    total = _shed_total(shed_stock)
    if total < SHED_NEAR_FULL:
        return selected
    try:
        fert = int((shed_stock or {}).get("FERTILIZER", 0) or 0)
    except Exception:
        return selected
    if fert <= 0:
        return selected
    dump = min(fert, total - SHED_TARGET)
    if dump <= 0:
        return selected

    selected.insert(0, ["SELL", "FERTILIZER", dump])
    _report["engaged"] += 1
    _report["dumped"] += dump
    return selected


# Backwards-compatible alias for direct stage wiring.
def _fert_liquidate_selected(out, obs, features):
    market = out.get("market") if isinstance(out, dict) else None
    if not isinstance(market, list):
        return False
    shed = None
    try:
        shed = obs["private"].get("shed")
    except Exception:
        pass
    before = len(market)
    apply(obs, market, enabled=True, shed_stock=shed,
          max_orders=getattr(features, "max_market_orders_per_turn", 10))
    return len(market) != before
