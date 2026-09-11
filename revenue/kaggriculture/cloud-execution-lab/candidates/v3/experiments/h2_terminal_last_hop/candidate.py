# SPDX-License-Identifier: Apache-2.0
"""Exact evaluator entrypoint for default-OFF H2 terminal last-hop rescue."""
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
import r04_h2_terminal_last_hop as h2  # noqa: E402

LIVE_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "h2_terminal_last_hop": True,
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

agent = h2.install(_parent, enabled=True)
