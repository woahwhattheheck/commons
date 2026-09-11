#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact evaluator entrypoint for the H9 R04/E20 experiment.

This file changes no gameplay policy.  It binds the experiment to the same shipped
V3.1 R04 knobs used by ``apply_v3.PARAMS`` and exports the resulting module-level
``agent`` so official paired runners do not need to reconstruct the composition by hand.

The wrapper remains packaging-neutral: this file lives under ``experiments/**`` and is
not included by ``build_v3.source_shas()`` / the candidate archive.
"""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve()
EXPERIMENTS = HERE.parents[1]
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
for path in (EXPERIMENTS, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from h9_r04_e20_hire_guard import install as install_h9  # noqa: E402
from r04_full_router import install as install_r04  # noqa: E402

# Exact shipped V3.1 R04 knobs from apply_v3.PARAMS / ready submission config.
BASE = install_r04(
    None,
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
)

agent = install_h9(BASE, enabled=True)

# Small machine-readable custody surface for evaluator receipts.
H9_EVALUATOR_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "h9_e20_enabled": True,
    "e20_max_hires_per_day": 3,
    "e20_min_unwatered_crops": 3,
}
