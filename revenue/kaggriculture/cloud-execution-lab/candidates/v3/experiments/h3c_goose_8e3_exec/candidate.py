# SPDX-License-Identifier: Apache-2.0
"""Shipped 8e3 V3.1 + exact reviewed H3c goose rescue entrypoint."""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
OVERLAY = V3 / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_full_router as base  # noqa: E402
import h3c_goose_eod_cap_rescue as h3c  # noqa: E402

CURRENT_8E3_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "r04_kill_late_water": False,
    "r04_strawberry_endgame": False,
    "r04_strawberry_max_plants": 8,
    "r04_no_late_sale_advance": True,
    "r04_no_late_sale_advance_step": 648,
    "r04_strawberry_topup": True,
    "r04_b5_carrot_fertilizer": True,
    "r04_b5_jit_fertilize": True,
}

_parent = base.install(
    None,
    horizon=CURRENT_8E3_CONFIG["r04_sale_horizon"],
    opening=CURRENT_8E3_CONFIG["r04_open_roundtrip"],
    row_order=CURRENT_8E3_CONFIG["r04_row_order"],
    evening_flush=CURRENT_8E3_CONFIG["r04_evening_flush"],
    sale_fertilizer=CURRENT_8E3_CONFIG["r04_sale_fertilizer"],
    cattle_early=CURRENT_8E3_CONFIG["r04_cattle_early"],
    kill_late_water=CURRENT_8E3_CONFIG["r04_kill_late_water"],
    strawberry_endgame=CURRENT_8E3_CONFIG["r04_strawberry_endgame"],
    strawberry_max_plants=CURRENT_8E3_CONFIG["r04_strawberry_max_plants"],
    no_late_sale_advance=CURRENT_8E3_CONFIG["r04_no_late_sale_advance"],
    no_late_sale_advance_step=CURRENT_8E3_CONFIG["r04_no_late_sale_advance_step"],
    strawberry_topup=CURRENT_8E3_CONFIG["r04_strawberry_topup"],
    b5_carrot_fertilizer=CURRENT_8E3_CONFIG["r04_b5_carrot_fertilizer"],
    b5_jit_fertilize=CURRENT_8E3_CONFIG["r04_b5_jit_fertilize"],
)
agent = h3c.install(_parent, enabled=True)
