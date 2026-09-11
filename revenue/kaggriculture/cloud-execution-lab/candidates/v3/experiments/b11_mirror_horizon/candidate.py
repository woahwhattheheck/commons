#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact evaluator entrypoint for B11 mirror-adaptive horizon."""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
for path in (HERE.parent, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from b11_mirror_horizon import REPORT, install  # noqa: E402

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

B11_EVALUATOR_CONFIG = {
    "r04_sale_horizon_baseline": 8,
    "r04_sale_horizon_mirror": 10,
    "mirror_streak_required": 8,
    "mirror_signature": ["tiles", "farmer", "hands", "unlocked_quadrants", "hires_today"],
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "b11_enabled": True,
}

B11_REPORT = REPORT
