#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact shipped a612 R04 tuple for the post-ship JIT interaction screen.

Evaluation only.  This file does not change package/default/source authority.
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

agent = base.install(
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
