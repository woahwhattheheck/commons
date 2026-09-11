# SPDX-License-Identifier: Apache-2.0
"""Evaluation-only composition hook for Riot L3 + ASTRA H4.

This file is outside overlay/** and is not part of the deterministic V3 package.  It
exists only to give the official evaluator one unambiguous way to arm both already-
gated mechanisms without changing defaults or integration ownership.

The module-level ``agent`` pins the existing V3.1 R04 baseline explicitly before
turning on H4 + L3.  This is intentional: the overlay module's source defaults are
not the shipped V3.1 package defaults, so a raw evaluator import must not rely on
``None`` preserving those source defaults.
"""

from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_full_router as base  # noqa: E402
import r04_h4_strawberry as h4  # noqa: E402


# Existing deterministic V3.1 R04 settings from apply_v3.py.  Keep these explicit
# so the evaluator arm is comparable to V3.1/L3 rather than to r04_full_router.py's
# source defaults (several of which are intentionally off).
V31_SALE_HORIZON = 8
V31_OPEN_ROUNDTRIP = 0
V31_ROW_ORDER = True
V31_EVENING_FLUSH = True
V31_SALE_FERTILIZER = True
V31_CATTLE_EARLY = True
V31_STRAWBERRY_MAX_PLANTS = 8


def install_joint(host=None, horizon=V31_SALE_HORIZON,
                  opening=V31_OPEN_ROUNDTRIP, row_order=V31_ROW_ORDER,
                  evening_flush=V31_EVENING_FLUSH,
                  sale_fertilizer=V31_SALE_FERTILIZER,
                  cattle_early=V31_CATTLE_EARLY,
                  no_late_sale_advance_step=648):
    """Return the exact V3.1 baseline with H4 + L3 enabled.

    L1/L2 are pinned off for this factorial arm.  H4's own reconcile function
    detects the L3 globals and becomes exact identity/no-debt at and after the
    configured cutoff.
    """
    candidate = h4.install(host, horizon, opening, row_order, evening_flush,
                           sale_fertilizer, cattle_early, strawberry_topup=True)
    # Pin the other experimental late-game lanes off as part of the arm contract,
    # then enable only L3.  This also prevents prior module state in a reused
    # evaluator process from silently contaminating the candidate.
    base.install(kill_late_water=False,
                 strawberry_endgame=False,
                 strawberry_max_plants=V31_STRAWBERRY_MAX_PLANTS,
                 no_late_sale_advance=True,
                 no_late_sale_advance_step=no_late_sale_advance_step)
    return candidate


# Standard evaluator entrypoint. Importing this module arms exactly the shipped
# V3.1 R04 baseline + H4 + L3 and exposes the same module-level callable contract
# as a normal Kaggriculture agent.  This avoids an untracked ad-hoc wrapper in the
# benchmark harness.
agent = install_joint()
