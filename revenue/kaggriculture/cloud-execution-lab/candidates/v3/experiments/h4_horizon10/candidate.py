# SPDX-License-Identifier: Apache-2.0
"""Exact H4 + horizon-10 evaluator arm for V3.1 interaction testing.

This stacked experiment intentionally changes no H4 logic. It imports the reviewed
H4 live-R04 seam and pins the ready-submission R04 tuple explicitly, with the single
parameter change ``r04_sale_horizon: 8 -> 10``. The module is outside ``overlay/**``
and therefore is not a deterministic V3 package input or a default-policy change.
"""

from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
H4_ROOT = V3_ROOT / "experiments" / "h4_strawberry"
OVERLAY = V3_ROOT / "overlay"
for path in (H4_ROOT, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_h4_strawberry as h4  # noqa: E402

# Exact live V3.1 R04 tuple, changing only sale horizon 8 -> 10 and arming H4.
CONFIG = {
    "r04_sale_horizon": 10,
    "r04_opening_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "r04_strawberry_topup": True,
}

agent = h4.install(
    horizon=CONFIG["r04_sale_horizon"],
    opening=CONFIG["r04_opening_roundtrip"],
    row_order=CONFIG["r04_row_order"],
    evening_flush=CONFIG["r04_evening_flush"],
    sale_fertilizer=CONFIG["r04_sale_fertilizer"],
    cattle_early=CONFIG["r04_cattle_early"],
    strawberry_topup=CONFIG["r04_strawberry_topup"],
)
