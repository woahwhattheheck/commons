# SPDX-License-Identifier: Apache-2.0
"""Evaluation-only composition hook for Riot L3 + ASTRA H4.

This file is outside overlay/** and is not part of the deterministic V3 package.  It
exists only to give the official evaluator one unambiguous way to arm both already-
gated mechanisms without changing defaults or integration ownership.
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


# Exact shipped V3.1 baseline knobs from apply_v3.PARAMS / ready submission config.
# The only experimental factors in this evaluator arm are H4 strawberry_topup and
# L3 no_late_sale_advance at the frozen cutoff.
JOINT_EVALUATOR_CONFIG = {
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "r04_kill_late_water": False,
    "r04_strawberry_endgame": False,
    "h4_strawberry_topup": True,
    "r04_no_late_sale_advance": True,
    "r04_no_late_sale_advance_step": 648,
}


def install_joint(host=None, horizon=8, opening=0, row_order=True,
                  evening_flush=True, sale_fertilizer=True, cattle_early=True,
                  no_late_sale_advance_step=648):
    """Return H4's agent on the shipped V3.1 baseline with Riot L3 enabled.

    The defaults intentionally pin the ready-submission V3.1 R04 baseline.  L1/L2 are
    explicitly disabled so a raw-file evaluator import changes exactly two factors:
    H4 strawberry top-up and L3 late-sale-advance suppression.  H4's reconcile function
    detects the L3 globals and becomes exact identity/no-debt at and after the cutoff.
    """
    candidate = h4.install(host, horizon, opening, row_order, evening_flush,
                           sale_fertilizer, cattle_early, strawberry_topup=True)
    base.install(kill_late_water=False,
                 strawberry_endgame=False,
                 no_late_sale_advance=True,
                 no_late_sale_advance_step=no_late_sale_advance_step)
    return candidate


# Standard evaluator entrypoint. Importing this module pins the shipped V3.1 baseline,
# arms exactly H4 + L3, and exposes the same module-level callable contract as a normal
# Kaggriculture agent. This avoids hidden caller config/path reconstruction in the bench.
agent = install_joint()
