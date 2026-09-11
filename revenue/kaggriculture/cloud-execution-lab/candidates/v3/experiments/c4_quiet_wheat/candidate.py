# SPDX-License-Identifier: Apache-2.0
"""C4 experiment: move already-planned WHEAT sales into genuinely quieter slots.

This is experiment-only. It reuses R04/E184's existing projected-stock, debt,
pickup/purchase, route-boundary and order-cap machinery. The only additional
eligibility is for WHEAT, the one product still excluded by live V3.1 E184:

* current own market row count is strictly lower than the due tape row count;
* moving earlier crosses no deterministic public WHEAT town-demand tick.

No hidden rival state is read. Non-WHEAT behavior is delegated byte-for-byte to
R04's existing reserve_sales implementation.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
# Source tree keeps R04 under overlay/. Deterministic submission archives flatten
# those same package-input bytes beside main.py. Support both explicitly so the
# experiment module itself is identical between focused source tests and a
# materialized practice gate.
SOURCE = ROOT / "overlay" if (ROOT / "overlay" / "r04_full_router.py").is_file() else ROOT
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import r04_full_router as r04  # noqa: E402

WHEAT_SHOPS = frozenset({
    "BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "ICE_CREAM_SHOP", "FARMERS_MARKET",
})
_BASE_RESERVE = r04.reserve_sales
_CURRENT_SHOPS: tuple[str, ...] = ()


def crosses_public_wheat_demand(step: int, due_step: int, shops) -> bool:
    """Whether advancing due->step crosses deterministic public WHEAT demand.

    Market orders execute before town consumption. A sale moved to ``step``
    therefore crosses every demand tick k with step <= k < due_step.
    """
    step, due_step = int(step), int(due_step)
    if due_step <= step:
        return False
    if any(k % 24 == 0 for k in range(step, due_step)):
        return True
    if any(shop in WHEAT_SHOPS for shop in shops):
        if any(k % 4 == 0 for k in range(step, due_step)):
            return True
    return False


def _filtered_tape(action, tape, step):
    """Hide only ineligible future WHEAT SELL rows from E184's reservation scan."""
    horizon = r04.SALE_HORIZON if step >= 144 else 1
    end = min(r04.LAST_STEP, step + horizon, (step // 72 + 1) * 72 - 1)
    current_rows = len(action.get("market") or [])
    shadow = list(tape)
    for due_step in range(step + 1, end + 1):
        future = tape[due_step]
        market = list(future.get("market") or [])
        if not any(len(o) >= 3 and o[:2] == ["SELL", "WHEAT"] for o in market):
            continue
        due_rows = len([o for o in market if o])
        eligible = (
            current_rows < due_rows
            and not crosses_public_wheat_demand(step, due_step, _CURRENT_SHOPS)
        )
        if eligible:
            continue
        copied = dict(future)
        copied["market"] = [
            list(o) if isinstance(o, list) else o
            for o in market
            if not (isinstance(o, list) and len(o) >= 3 and o[:2] == ["SELL", "WHEAT"])
        ]
        shadow[due_step] = copied
    return shadow


def reserve_sales_c4(action, view, state, tape, step):
    """Delegate to exact E184 with only guarded WHEAT visibility added."""
    shadow = _filtered_tape(action, tape, int(step))
    prior = r04.SALE_EXCLUDED
    try:
        # Live V3.1 already permits FERTILIZER. C4 removes only WHEAT from the
        # exclusion while the exact base reservation function runs.
        r04.SALE_EXCLUDED = tuple(item for item in prior if item != "WHEAT")
        return _BASE_RESERVE(action, view, state, shadow, step)
    finally:
        r04.SALE_EXCLUDED = prior


def install(*, enabled: bool = True):
    """Return exact live V3.1 R04, optionally with C4's reservation hook."""
    global _CURRENT_SHOPS
    base = r04.install(None, 8, 0, True, True, True, True)
    if not enabled:
        r04.reserve_sales = _BASE_RESERVE
        return base
    r04.reserve_sales = reserve_sales_c4

    def agent(observation, configuration=None):
        global _CURRENT_SHOPS
        _CURRENT_SHOPS = tuple((observation.get("town") or {}).get("unlocked_shops") or ())
        return base(observation, configuration)

    agent.c4_enabled = True
    agent.parent = base
    return agent


agent = install(enabled=True)
