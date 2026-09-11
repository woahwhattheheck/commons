#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact evaluator entrypoint for the B8 additive budget-guard experiment."""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
for path in (HERE.parent, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from b8_budget_guard import REPORT, install  # noqa: E402

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

B8_EVALUATOR_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "b8_additive_budget_guard": True,
    "b8_scope": "V219_V233_FIXED_COST_FUTURE_NATIVE_ONLY",
}

B8_REPORT = REPORT
