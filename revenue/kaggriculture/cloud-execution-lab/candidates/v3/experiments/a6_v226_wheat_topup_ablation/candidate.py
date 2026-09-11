#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evidence-only ablation of V226 dynamic WHEAT top-ups on shipped a612.

V226 is a narrow wrapper: after the inherited action is produced, it may append
one bounded ``BUY_PRODUCT WHEAT`` order to cover a shortage in an already
scheduled next-step shed-adjacent WHEAT pickup.  This candidate disables only
that helper while the exact shipped outer R04/H4/L3 chain runs, then restores
it in ``finally``.  Native tape wheat purchases, V233 sheep wheat purchases,
V234 rescue buys, worker commands, and every later layer remain untouched.
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

_ORIGINAL_TOPUP = base._v226_topup
REPORT = {"calls": 0}


def _no_v226_topup(_observation, action, _state, _configuration=None):
    return action


def agent(observation, configuration=None):
    REPORT["calls"] += 1
    previous = base._v226_topup
    base._v226_topup = _no_v226_topup
    try:
        return BASE_AGENT(observation, configuration)
    finally:
        base._v226_topup = previous


agent.telemetry = REPORT
