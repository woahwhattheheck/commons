#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current-root 6e5 control adapter for the A6 V226 WHEAT-topup ablation."""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as base  # noqa: E402

CURRENT_PARENT = "6e5e3c7cc5302d6db4b702cc4fd7c8ca721d7b8a"
CURRENT_R04_BLOB = "7edacbfb4916b8f241b689ded6643240ca02a9ec"
CURRENT_6E5 = {
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
    "b5_carrot_fertilizer": True,
    "b5_jit_fertilize": True,
}

agent = base.install(host=None, **CURRENT_6E5)
