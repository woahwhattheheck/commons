#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact evaluator entrypoint for the E7 center-tick timing experiment."""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
for path in (HERE.parent, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from e7_center_tick_veto import REPORT, install  # noqa: E402

# Exact ready-submission V3.1 R04 tuple. E7 changes only whether E184 may
# reserve non-fertilizer future sales on runtime-proven town-center ticks.
agent = install(
    None,
    enabled=True,
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
)

E7_EVALUATOR_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "e7_center_tick_veto": True,
    "e7_requires_townCenterSellInterval": 24,
    "e7_interval_type": "literal-int",
    "e7_nonstandard_or_malformed_config": "exact-parent",
    "e7_preserve_fertilizer": True,
}

E7_REPORT = REPORT
