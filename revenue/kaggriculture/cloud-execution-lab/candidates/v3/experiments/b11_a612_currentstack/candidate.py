#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evidence-only B11 composition on exact shipped a612 V3.1 R04.

The reviewed B11 classifier is transplanted byte-for-byte.  This wrapper changes no
classifier logic: it first installs the exact a612 score-facing H4 + rival-gated-L3
R04 tuple, then lets the reviewed B11 installer bind the inherited H8 fields.  The
second install intentionally leaves the newer a612-only knobs untouched because R04
updates them only when the corresponding argument is not None.
"""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_full_router as r04  # noqa: E402

CURRENT_A612_CONFIG = {
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
}

# Prime all current-a612-only R04 globals.  No policy state is created until the
# returned callable is actually invoked, so discarding this callable is state-neutral.
r04.install(None, **CURRENT_A612_CONFIG)

from b11_mirror_horizon import REPORT, install  # noqa: E402

# Exact reviewed donor installer.  Its older six-parameter call refreshes the H8
# fields but does not touch a612-only knobs because their defaults are None.
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

B11_REPORT = REPORT
B11_CURRENT_STACK = dict(CURRENT_A612_CONFIG)
agent.telemetry = REPORT
