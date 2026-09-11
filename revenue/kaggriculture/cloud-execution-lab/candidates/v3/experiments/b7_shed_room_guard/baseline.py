#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact ready-V3.1 R04 baseline for the B7 execution gate."""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

from r04_full_router import install as install_r04  # noqa: E402

agent = install_r04(
    None,
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
)

B7_BASELINE_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
}
