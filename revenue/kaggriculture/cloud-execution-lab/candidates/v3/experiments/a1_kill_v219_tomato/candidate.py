#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evidence-only ablation of V219's late TOMATO investment on shipped a612.

The exact shipped outer R04/H4/L3 agent is called unchanged except that the
V219 qualification predicate is forced false during this candidate's call.
That removes only V219's own late land/seed/hire/worker/sale program; every
parent and later layer remains in the same call chain.  The original predicate
is restored in ``finally`` so the experiment has no ambient module side effect.
"""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as base  # noqa: E402

LIVE_A612 = {
    "horizon": 8,
    "opening": 0,
    "row_order": True,
    "evening_flush": True,
    "sale_fertilizer": True,
    "cattle_early": True,
    "kill_late_water": False,
    "strawberry_endgame": False,
    "strawberry_max_plants": 8,
    "no_late_sale_advance": True,
    "no_late_sale_advance_step": 648,
    "strawberry_topup": True,
}

BASE_AGENT = base.install(
    None,
    LIVE_A612["horizon"],
    LIVE_A612["opening"],
    LIVE_A612["row_order"],
    LIVE_A612["evening_flush"],
    LIVE_A612["sale_fertilizer"],
    LIVE_A612["cattle_early"],
    LIVE_A612["kill_late_water"],
    LIVE_A612["strawberry_endgame"],
    LIVE_A612["strawberry_max_plants"],
    LIVE_A612["no_late_sale_advance"],
    LIVE_A612["no_late_sale_advance_step"],
    LIVE_A612["strawberry_topup"],
)

_ORIGINAL_QUALIFIES = base._v219_qualifies
REPORT = {"calls": 0, "step432_calls": 0}


def _never_v219(_observation, _native):
    return False


def agent(observation, configuration=None):
    REPORT["calls"] += 1
    try:
        if int(observation.get("step", -1)) == 432:
            REPORT["step432_calls"] += 1
    except (AttributeError, TypeError, ValueError):
        pass

    previous = base._v219_qualifies
    base._v219_qualifies = _never_v219
    try:
        return BASE_AGENT(observation, configuration)
    finally:
        base._v219_qualifies = previous


agent.telemetry = REPORT
