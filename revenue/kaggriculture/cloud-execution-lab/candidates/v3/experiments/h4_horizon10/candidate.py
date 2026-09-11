# SPDX-License-Identifier: Apache-2.0
"""Exact evaluator entrypoint for the H4 x sale-horizon=10 interaction arm.

This module is intentionally outside ``overlay/**`` and therefore outside deterministic
V3 package inputs.  It composes the reviewed H4 strawberry same-row reservation source
with the already-measured H13 parameter change while pinning every other live R04 knob.

The control tuple is the ready V3.1/H4 runtime tuple with sale horizon 8.  The candidate
changes exactly one value: ``horizon=10``.  Importing this module arms H4 and exposes the
standard module-level ``agent`` used by paired evaluator runners.
"""

from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
H4_DIR = V3_ROOT / "experiments" / "h4_strawberry"
OVERLAY = V3_ROOT / "overlay"
for path in (H4_DIR, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_h4_strawberry as h4  # noqa: E402

CONTROL_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_opening_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "h4_strawberry_topup": True,
}

EXPERIMENT_CONFIG = dict(CONTROL_CONFIG)
EXPERIMENT_CONFIG["r04_sale_horizon"] = 10

agent = h4.install(
    horizon=EXPERIMENT_CONFIG["r04_sale_horizon"],
    opening=EXPERIMENT_CONFIG["r04_opening_roundtrip"],
    row_order=EXPERIMENT_CONFIG["r04_row_order"],
    evening_flush=EXPERIMENT_CONFIG["r04_evening_flush"],
    sale_fertilizer=EXPERIMENT_CONFIG["r04_sale_fertilizer"],
    cattle_early=EXPERIMENT_CONFIG["r04_cattle_early"],
    strawberry_topup=EXPERIMENT_CONFIG["h4_strawberry_topup"],
)
