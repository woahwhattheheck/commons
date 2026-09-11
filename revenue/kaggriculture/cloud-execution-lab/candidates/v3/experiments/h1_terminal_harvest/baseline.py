#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact ready-V3.1 control entrypoint for the H1 realization gate.

This is evaluation-only.  It binds the same R04 tuple used by H1's candidate
without installing the H1 transform, so paired traces differ only if H1 changes
an emitted action and its downstream world state.
"""
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

BASELINE_EVALUATOR_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "h1_terminal_harvest": False,
    "official_interpreter_commit": "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
}
