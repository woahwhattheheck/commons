# SPDX-License-Identifier: Apache-2.0
"""Exact V3.1 evaluator entrypoint for H3c goose EOD cap rescue."""
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

LIVE_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "h3c_goose_eod_cap_rescue": True,
}

_parent = base.install(
    None,
    horizon=LIVE_CONFIG["r04_sale_horizon"],
    opening=LIVE_CONFIG["r04_open_roundtrip"],
    row_order=LIVE_CONFIG["r04_row_order"],
    evening_flush=LIVE_CONFIG["r04_evening_flush"],
    sale_fertilizer=LIVE_CONFIG["r04_sale_fertilizer"],
    cattle_early=LIVE_CONFIG["r04_cattle_early"],
)
agent = h3c.install(_parent, enabled=True)
