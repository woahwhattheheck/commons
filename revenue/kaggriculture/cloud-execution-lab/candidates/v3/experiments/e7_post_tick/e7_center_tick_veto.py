# SPDX-License-Identifier: Apache-2.0
"""E7 experiment: veto E184 advancement across guaranteed town-center ticks.

This is an experiment-only factor. It does not claim that waiting is always
economically better: the rival's current-step market queue is hidden and can
more than offset deterministic town consumption. The narrow factor therefore
does one measurable thing only: on guaranteed town-center consumption steps,
prevent E184 from pulling non-fertilizer future sales forward before the tick.

Authored/current SELL rows are untouched. FERTILIZER keeps the parent E184
behavior because the town center never consumes it.
"""
from __future__ import annotations

import copy

import r04_full_router as r04

_ORIGINAL_RESERVE = r04.reserve_sales

REPORT = {
    "center_tick_calls": 0,
    "counterfactual_activations": 0,
    "skipped_rows": 0,
    "skipped_units": 0,
    "trace": [],
}


def reset_report():
    REPORT["center_tick_calls"] = 0
    REPORT["counterfactual_activations"] = 0
    REPORT["skipped_rows"] = 0
    REPORT["skipped_units"] = 0
    REPORT["trace"] = []


def _new_nonfert_sell_rows(before_market, after_market):
    """Return E184-appended non-fertilizer SELL rows only."""
    rows = []
    for order in after_market[len(before_market):]:
        if (
            isinstance(order, list)
            and len(order) >= 3
            and order[0] == "SELL"
            and order[1] in r04.PRODUCTS
            and order[1] != "FERTILIZER"
        ):
            try:
                qty = int(order[2])
            except (TypeError, ValueError):
                continue
            if qty > 0:
                rows.append((order[1], qty))
    return rows


def guarded_reserve_sales(action, view, state, tape, step):
    """Preserve parent behavior except at guaranteed town-center ticks."""
    if step < r04.ADVANCE_START or step >= r04.LAST_STEP or step % 24 != 0:
        return _ORIGINAL_RESERVE(action, view, state, tape, step)

    REPORT["center_tick_calls"] += 1

    # Counterfactual telemetry only. The original reserve function mutates only
    # action/state, so deep copies keep this diagnostic path side-effect free.
    cf_action = copy.deepcopy(action)
    cf_state = copy.deepcopy(state)
    before_market = copy.deepcopy(cf_action.get("market") or [])
    _ORIGINAL_RESERVE(cf_action, view, cf_state, tape, step)
    skipped = _new_nonfert_sell_rows(before_market, cf_action.get("market") or [])
    if skipped:
        REPORT["counterfactual_activations"] += 1
        REPORT["skipped_rows"] += len(skipped)
        REPORT["skipped_units"] += sum(qty for _, qty in skipped)
        if len(REPORT["trace"]) < 256:
            REPORT["trace"].append(
                {
                    "step": int(step),
                    "rows": [{"item": item, "qty": qty} for item, qty in skipped],
                }
            )

    # Preserve parent exclusion semantics, but additionally exclude every item
    # consumed by the guaranteed town-center tick. FERTILIZER is the sole
    # product the town center never consumes, so it may retain parent behavior
    # iff the parent already allows it.
    old_excluded = r04.SALE_EXCLUDED
    extra = tuple(item for item in r04.PRODUCTS if item != "FERTILIZER")
    r04.SALE_EXCLUDED = tuple(dict.fromkeys((*old_excluded, *extra)))
    try:
        return _ORIGINAL_RESERVE(action, view, state, tape, step)
    finally:
        r04.SALE_EXCLUDED = old_excluded


def install(
    host=None,
    *,
    enabled=True,
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
):
    """Install exact V3.1 R04 knobs plus the default-off E7 experiment seam."""
    parent = r04.install(
        host,
        horizon=horizon,
        opening=opening,
        row_order=row_order,
        evening_flush=evening_flush,
        sale_fertilizer=sale_fertilizer,
        cattle_early=cattle_early,
    )
    r04.reserve_sales = guarded_reserve_sales if enabled else _ORIGINAL_RESERVE
    return parent
